"""Agent/tool evaluation: tool selection, bounds, completion, latency."""

from __future__ import annotations

from typing import Any


def evaluate_tool_selection(
    *,
    question: str,
    requested_kind: str,
    tools_used: list[str],
    tool_call_count: int,
    completed: bool,
    latency_ms: float,
    case,  # ToolCase-shaped
) -> dict[str, Any]:
    checks: list[bool] = []

    # Tool selection: workflow nodes map to tool families.
    expected = set(case.expected_tools)
    forbidden = set(case.forbidden_tools)
    used = set(tools_used)
    checks.append(bool(used & expected))
    checks.append(not (used & forbidden))
    checks.append(tool_call_count <= 8)  # bounds respected
    checks.append(completed)
    return {
        "case_id": case.case_id,
        "checks": checks,
        "passed": all(checks),
        "tool_call_count": tool_call_count,
        "latency_ms": latency_ms,
    }


def aggregate_agent_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {"cases": 0}
    passed = sum(1 for r in results if r["passed"])
    return {
        "cases": total,
        "pass_rate": round(passed / total, 4),
        "avg_tool_calls": round(sum(r["tool_call_count"] for r in results) / total, 3),
        "avg_latency_ms": round(sum(r["latency_ms"] for r in results) / total, 1),
        "completion_rate": round(
            sum(1 for r in results if all(r["checks"])) / total, 4
        ),
    }
