"""LangGraph investigation workflow.

Constructs the bounded state machine used by ``POST /api/v1/chat``: request
classification → scope resolution → query rewriting → retrieval
(documents/graph/analytics) → compression → evidence assembly → model
synthesis → claim verification → guardrails → optional review → formatting.
Tool calls, iterations, and graph depth are strictly bounded; unanswerable
questions abstain instead of looping.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.agents import nodes
from app.agents.state import InvestigationResult, InvestigationState

logger = get_logger(__name__)


class InvestigationWorkflow:
    """Compiles the graph once; runs investigations against it."""

    def __init__(self, *, router) -> None:  # noqa: ANN001 - ModelRouter
        self._router = router
        self.graph = self._compile()

    def _compile(self) -> StateGraph:
        graph = StateGraph(dict)

        def _ws_id(state) -> str | None:
            services = getattr(state, "__services__", None)
            if services is None and isinstance(state, dict):
                services = state.get("__services__")
            if isinstance(services, dict):
                return services.get("workspace_id")
            return getattr(services, "workspace_id", None)

        graph.add_node("classify_request", self._wrap(nodes.classify_request))
        graph.add_node("resolve_scope", self._wrap(
            lambda state, db: nodes.resolve_scope(state, db, workspace_id=_ws_id(state)),
            needs_db=True,
        ))
        graph.add_node("rewrite_query", self._wrap(nodes.rewrite_query))
        graph.add_node("plan_investigation", self._plan_node)
        graph.add_node("retrieve_documents", self._retrieve_node)
        graph.add_node("retrieve_graph", self._graph_node)
        graph.add_node("execute_analytics", self._analytics_node)
        graph.add_node("rerank_and_compress", self._wrap(nodes.rerank_and_compress))
        graph.add_node("assemble_evidence", self._assemble_node)
        graph.add_node("draft_analysis", self._draft_node)
        graph.add_node("await_local_model", self._await_node)
        graph.add_node("verify_claims", self._wrap(nodes.verify_claims))
        graph.add_node("check_guardrails", self._wrap(nodes.check_guardrails))
        graph.add_node("request_review", self._review_node)
        graph.add_node("format_response", self._format_node)
        graph.add_node("record_feedback", self._wrap(nodes.record_feedback))


        graph.set_entry_point("classify_request")
        graph.add_edge("classify_request", "resolve_scope")
        graph.add_edge("resolve_scope", "rewrite_query")
        graph.add_edge("rewrite_query", "plan_investigation")
        graph.add_conditional_edges(
            "plan_investigation",
            self._route_plan,
            {
                "analytics": "execute_analytics",
                "retrieval": "retrieve_documents",
                "graph": "retrieve_graph",
                "format": "format_response",
            },
        )
        graph.add_edge("execute_analytics", "retrieve_documents")
        graph.add_conditional_edges(
            "retrieve_documents",
            self._route_retrieval,
            {"found": "rerank_and_compress", "empty": "assemble_evidence"},
        )
        graph.add_edge("retrieve_graph", "assemble_evidence")
        graph.add_edge("rerank_and_compress", "assemble_evidence")
        graph.add_edge("assemble_evidence", "draft_analysis")
        graph.add_conditional_edges(
            "draft_analysis",
            self._route_draft,
            {
                "awaiting_local_model": "await_local_model",
                "reply_ready": "verify_claims",
                "abstain": "format_response",
            },
        )
        graph.add_conditional_edges(
            "await_local_model",
            self._route_await,
            {"reply_ready": "verify_claims", "abstain": "format_response"},
        )
        graph.add_conditional_edges(
            "verify_claims",
            lambda state: "check_guardrails" if state.get("verification_status") == "verified" else "format_response",
            {"check_guardrails": "check_guardrails", "format_response": "format_response"},
        )
        graph.add_conditional_edges(
            "check_guardrails",
            self._route_guardrails,
            {"request_review": "request_review", "format_response": "format_response"},
        )
        graph.add_conditional_edges(
            "request_review",
            self._route_review,
            {"format_response": "format_response", "review_requested": "format_response"},
        )
        graph.add_edge("format_response", "record_feedback")
        graph.add_edge("record_feedback", END)
        return graph.compile()

    @staticmethod
    def _plan_state_to_services(plan_state) -> dict:
        ws_id = getattr(plan_state, "workspace_id", None)
        if ws_id is None and isinstance(plan_state, dict):
            ws_id = plan_state.get("workspace_id")
        return {"workspace_id": ws_id}

    # --- node wrappers (db/session threaded through state["__services__"]) ---

    def _wrap(self, fn, *, needs_db: bool = False):  # noqa: ANN001
        def wrapped(state):
            if not isinstance(state, dict):
                return state
            services = state.get("__services__", {})
            self._sync_state(state)
            if needs_db:
                db = services.get("db")
                if db is None:
                    state["__errors__"] = state.get("__errors__", [])
                    state["__errors__"].append("missing db service for " + fn.__name__)
                    return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id")}
                fn(state["__state__"], db)
            else:
                fn(state["__state__"])
            result = {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id")}
            state["__services__"] = services
            return result

        return wrapped

    def _sync_state(self, state: dict) -> None:
        state["__state__"] = state.get("__state__", state.get("initial_state"))

    def _export(self, state: dict) -> dict:
        return {"__state__": state["__state__"], "__services__": state.get("__services__", {}).copy()}

    def _plan_node(self, state: dict) -> dict:
        state["__state__"] = state.get("__state__")
        planned = nodes.plan_investigation(state["__state__"])
        state["__plan__"] = planned
        plan_state = state["__state__"]
        return {
            "__state__": state["__state__"],
            "__services__": self._plan_state_to_services(plan_state),
            "__plan__": planned,
        }

    def _route_plan(self, state) -> str:
        plan: list[str] = state.get("__plan__") if isinstance(state, dict) else getattr(state, "__plan__", None) or ["format"]
        for step in plan:
            if step == "analytics":
                return "analytics"
            if step == "graph":
                return "graph"
            if step == "retrieval":
                return "retrieval"
        return "format"

    def _retrieve_node(self, state: dict) -> dict:
        services = state.get("__services__")
        if not isinstance(services, dict) or services.get("db") is None:
            return {"__state__": state["__state__"], "__services__": {}, "workspace_id": None, "__outcome__": "empty"}
        nodes.retrieve_documents(state["__state__"], db=services.get("db"))
        outcome = "found" if state["__state__"].candidates else "empty"
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id"), "__outcome__": outcome}

    def _route_retrieval(self, state) -> str:
        return state.get("__outcome__", "empty") if isinstance(state, dict) else getattr(state, "__outcome__", "empty")

    def _graph_node(self, state: dict) -> dict:
        services = state.get("__services__")
        if not isinstance(services, dict) or services.get("db") is None:
            return {"__state__": state["__state__"], "__services__": {}, "workspace_id": None}
        nodes.retrieve_graph(state["__state__"], db=services.get("db"))
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id")}

    def _analytics_node(self, state: dict) -> dict:
        services = state.get("__services__")
        if not isinstance(services, dict) or services.get("db") is None:
            return {"__state__": state["__state__"], "__services__": {}, "workspace_id": None}
        nodes.execute_analytics(state["__state__"], db=services.get("db"))
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id")}

    def _assemble_node(self, state: dict) -> dict:
        nodes.assemble_evidence(state["__state__"])
        return {"__state__": state["__state__"], "__services__": state.get("__services__", {})}

    def _draft_node(self, state: dict) -> dict:
        services = state.get("__services__")
        if not isinstance(services, dict) or services.get("db") is None:
            return {"__state__": state["__state__"], "__services__": {}, "workspace_id": None, "__draft_route__": "abstain"}
        route = nodes.draft_analysis(
            state["__state__"], db=services.get("db"), router=services.get("router", self._router)
        )
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id"), "__draft_route__": route}

    def _route_draft(self, state) -> str:
        return state.get("__draft_route__", "abstain") if isinstance(state, dict) else getattr(state, "__draft_route__", "abstain")

    def _await_node(self, state: dict) -> dict:
        services = state.get("__services__")
        if not isinstance(services, dict) or services.get("db") is None:
            return {"__state__": state["__state__"], "__services__": {}, "workspace_id": None, "__await_route__": "abstain"}
        route = nodes.await_local_model(state["__state__"], db=services.get("db"))
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id"), "__await_route__": route}

    def _route_await(self, state) -> str:
        return state.get("__await_route__", "abstain") if isinstance(state, dict) else getattr(state, "__await_route__", "abstain")

    def _review_node(self, state: dict) -> dict:
        services = state.get("__services__")
        if not isinstance(services, dict) or services.get("db") is None:
            return {"__state__": state["__state__"], "__services__": {}, "workspace_id": None, "__review_route__": "format_response"}
        route = nodes.request_review(state["__state__"], db=services.get("db"))
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id"), "__review_route__": route}

    def _route_guardrails(self, state) -> str:
        state_ = state["__state__"] if isinstance(state, dict) else getattr(state, "__state__", state)
        state_.tool_calls += 0
        if any("flagged" in finding for finding in state_.guardrail_findings):
            return "request_review"
        return "format_response"

    def _route_review(self, state) -> str:
        return state.get("__review_route__", "format_response") if isinstance(state, dict) else getattr(state, "__review_route__", "format_response")

    def _format_node(self, state: dict) -> dict:
        services = state.get("__services__") or {}
        if not isinstance(services, dict):
            services = {}
        result = nodes.format_response(state["__state__"])
        return {"__state__": state["__state__"], "__services__": services, "workspace_id": services.get("workspace_id"), "result": result}

    # --- public API -------------------------------------------------------------

    def run(
        self,
        *,
        db: Session,
        workspace_id: str,
        user_id: str,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> InvestigationResult:
        settings = get_settings()
        state = InvestigationState(
            request_id=f"inv_{workspace_id[:8]}",
            workspace_id=workspace_id,
            user_id=user_id,
            question=question,
            conversation_history=[{k: v for k, v in (m or {}).items() if k in {"role", "content"}} for m in (conversation_history or [])][-10:],
        )
        payload: dict[str, Any] = {
            "__state__": state,
            "__services__": {"db": db, "router": self._router, "workspace_id": workspace_id},
        }
        final = self.graph.invoke(
            payload,
            config={
                "recursion_limit": max(2 * settings.agent_max_iterations, 24),
            },
        )
        result = final.get("result")
        if isinstance(result, InvestigationResult):
            return result
        # Fail closed: an internal routing error yields an abstention, not a
        # fabricated answer.
        logger.error("investigation workflow did not produce a result")
        return InvestigationResult(
            status="abstained",
            question=question,
            abstention_reason="the investigation workflow could not complete; retry",
        )
