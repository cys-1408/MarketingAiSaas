"""Real MCP server exposing approved, typed, read-only tools.

Implements the MCP JSON-RPC 2.0 protocol over stdio ( initialize /
tools/list / tools/call ).  Tools reuse the same domain services and
authorization logic as FastAPI — MCP is never a bypass around tenant
security.  Requests carry a workspace API token; every call re-verifies
membership and capability.  Only read-only tools are exposed; any
state-changing action must go through the reviewed SaaS API/approval queue.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from app.core.tenancy import AuthorizationError, authorize_workspace
from app.db.session import session_scope
from app.tools.analytics import AnalyticsService
from app.tools.feedback import FeedbackService
from app.tools.products import ProductService


class ToolError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    side_effect: str  # none (read-only set)

    def public(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {"sideEffect": "none", "readOnly": True},
        }


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_campaign_summary",
        description="Metric totals for one campaign in a date window.",
        input_schema={
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "campaign_id": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["workspace_id", "campaign_id", "start_date", "end_date"],
        },
        side_effect="none",
    ),
    ToolSpec(
        name="compare_campaigns",
        description="Compare up to 5 campaigns on selected metrics.",
        input_schema={
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "campaign_ids": {"type": "array", "items": {"type": "string"}},
                "metric_names": {"type": "array", "items": {"type": "string"}},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["workspace_id", "campaign_ids", "metric_names", "start_date", "end_date"],
        },
        side_effect="none",
    ),
    ToolSpec(
        name="search_customer_feedback",
        description="Search permitted customer feedback records.",
        input_schema={
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "query": {"type": "string"},
                "date_start": {"type": "string"},
                "date_end": {"type": "string"},
            },
            "required": ["workspace_id"],
        },
        side_effect="none",
    ),
    ToolSpec(
        name="get_product_facts",
        description="Approved product facts and claims.",
        input_schema={
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "product_id": {"type": "string"},
                "topic": {"type": "string"},
            },
            "required": ["workspace_id"],
        },
        side_effect="none",
    ),
)


def _api_token_authenticate(token: str, workspace_id: str) -> None:
    """Authenticate the caller with a workspace API token.

    Token format mirrors session tokens; membership/permission are checked
    server-side before each tool call (never client-decided).
    """
    from app.core.security import SecurityError, verify_session_token
    from app.db.session import get_session_factory

    try:
        claims = verify_session_token(token)
    except SecurityError as exc:
        raise ToolError("unauthorized", "invalid or expired API token") from exc
    if claims.workspace_id != workspace_id:
        raise ToolError("forbidden", "token is not valid for this workspace")
    with session_scope() as db:
        authorize_workspace(
            db, user_id=claims.user_id, workspace_id=workspace_id, required_capability=2
        )


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute an allowlisted, read-only tool under verified authorization."""
    if name not in {tool.name for tool in TOOLS}:
        raise ToolError("unknown_tool", f"tool '{name}' is not published")
    workspace_id = str(arguments.get("workspace_id", ""))
    token = str(arguments.get("_meta_token", ""))
    if not workspace_id or not token:
        raise ToolError("unauthorized", "workspace_id and API token are required")
    _api_token_authenticate(token, workspace_id)
    with session_scope() as db:
        if name == "get_campaign_summary":
            return AnalyticsService(db).get_campaign_summary(
                workspace_id=workspace_id,
                campaign_id=str(arguments["campaign_id"]),
                start_date=str(arguments["start_date"]),
                end_date=str(arguments["end_date"]),
                user_id=_claims_user(token),
            )
        if name == "compare_campaigns":
            return AnalyticsService(db).compare_campaigns(
                workspace_id=workspace_id,
                campaign_ids=list(arguments["campaign_ids"]),
                metric_names=list(arguments["metric_names"]),
                start_date=str(arguments["start_date"]),
                end_date=str(arguments["end_date"]),
                user_id=_claims_user(token),
            )
        if name == "search_customer_feedback":
            return FeedbackService(db).search(
                workspace_id=workspace_id,
                user_id=_claims_user(token),
                query=str(arguments.get("query", "")),
                date_start=arguments.get("date_start"),
                date_end=arguments.get("date_end"),
            )
        if name == "get_product_facts":
            return ProductService(db).get_product_facts(
                workspace_id=workspace_id,
                user_id=_claims_user(token),
                product_id=arguments.get("product_id"),
                topic=arguments.get("topic"),
            )
    raise ToolError("unknown_tool", name)  # pragma: no cover


def _claims_user(token: str) -> str:
    from app.core.security import verify_session_token

    return verify_session_token(token).user_id


JSONRPC_PARSE_ERROR = -32700
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_REQUEST = -32602


class McpStdioServer:
    """JSON-RPC 2.0 over stdio lines: initialize, tools/list, tools/call."""

    def __init__(self, *, read=None, write=None) -> None:  # noqa: ANN001
        self._read = read or sys.stdin.readline
        self._write = write or (lambda text: (sys.stdout.write(text), sys.stdout.flush()))

    def handle(self, raw: str) -> dict[str, Any] | None:
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            return self._error(None, JSONRPC_PARSE_ERROR, "parse error")
        if not isinstance(request, dict) or "method" not in request:
            return self._error(None, JSONRPC_INVALID_REQUEST, "invalid request")
        request_id = request.get("id")
        method = request["method"]
        params = request.get("params") or {}
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0", "id": request_id,
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "marketing-copilot-mcp", "version": "0.1.0"},
                    },
                }
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0", "id": request_id,
                    "result": {"tools": [tool.public() for tool in TOOLS]},
                }
            if method == "tools/call":
                name = params.get("name", "")
                arguments = params.get("arguments") or {}
                try:
                    result = call_tool(name, arguments)
                except ToolError as exc:
                    return {
                        "jsonrpc": "2.0", "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": exc.detail}],
                            "isError": True,
                            "errorCode": exc.code,
                        },
                    }
                return {
                    "jsonrpc": "2.0", "id": request_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, default=str)}
                        ],
                        "isError": False,
                    },
                }
            if method == "notifications/initialized":
                return None
            return self._error(request_id, JSONRPC_METHOD_NOT_FOUND, f"unknown method {method}")
        except Exception as exc:  # noqa: BLE001 - convert to protocol error
            return self._error(request_id, JSONRPC_INVALID_REQUEST, f"internal error: {exc}")

    def serve_forever(self) -> None:
        """Blocking loop over stdin lines (documented startup in README)."""
        while True:
            line = self._read()
            if not line:
                return
            response = self.handle(line if isinstance(line, str) else line.decode())
            if response is not None:
                self._write(json.dumps(response) + "\n")

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
