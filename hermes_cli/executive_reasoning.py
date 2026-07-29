"""Operator-safe Executive Reasoning Engine diagnostics."""

from __future__ import annotations

import json
from typing import Any

from gateway.executive_reasoning import (
    ReasoningPlanningRequest,
    build_default_reasoning_engine,
    build_default_reasoning_mode_registry,
    build_reasoning_status,
    render_reasoning_result_for_prompt,
)


def reasoning_status() -> dict[str, Any]:
    return build_reasoning_status()


def reasoning_diagnostics() -> dict[str, Any]:
    engine = build_default_reasoning_engine()
    result = engine.prepare(
        ReasoningPlanningRequest(
            correlation_id="eo_reasoning_diagnostic",
            tenant_id="diagnostic-tenant",
            actor_id="diagnostic-user",
            normalized_user_request="What meetings do I have today?",
            request_classification="executive_status",
            context_source_counts={"current_request_metadata": 1},
            evidence_refs=(),
            safety_state="normal_non_executing",
            trace_metadata={"diagnostic": True},
        )
    )
    return {
        "status": "ok",
        "external_calls_enabled": False,
        "live_execution_enabled": False,
        "execution_boundary": "not_executed",
        "reasoning_plan": result.reasoning_plan.safe_trace(),
        "response_plan": result.response_plan.safe_trace(),
        "rendered_plan_digest": _digest(render_reasoning_result_for_prompt(result)),
        "redacted": True,
    }


def reasoning_plans() -> dict[str, Any]:
    registry = build_default_reasoning_mode_registry()
    return {
        "status": "ok",
        "execution_boundary": "not_executed",
        "skill_execution": "selected_not_executed",
        "modes": [
            {
                "mode_id": mode_id,
                "expected_structure": list(registry.lookup(mode_id).expected_structure),
            }
            for mode_id in registry.mode_ids()
        ],
        "confidence_levels": [
            "known",
            "derived",
            "assumed",
            "unavailable",
            "conflicting",
            "unknown",
        ],
        "redacted": True,
    }


def cmd_status(args: Any) -> None:
    del args
    print(json.dumps(reasoning_status(), sort_keys=True))


def cmd_diagnostics(args: Any) -> None:
    del args
    print(json.dumps(reasoning_diagnostics(), sort_keys=True))


def cmd_plans(args: Any) -> None:
    del args
    print(json.dumps(reasoning_plans(), sort_keys=True))


def register_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "reasoning",
        help="Inspect Executive Reasoning Engine state",
    )
    parser.set_defaults(func=cmd_status)
    subs = parser.add_subparsers(dest="reasoning_command")
    status = subs.add_parser("status", help="Show Executive Reasoning status")
    status.set_defaults(func=cmd_status)
    diagnostics = subs.add_parser(
        "diagnostics",
        help="Run a synthetic non-external reasoning diagnostic",
    )
    diagnostics.set_defaults(func=cmd_diagnostics)
    plans = subs.add_parser("plans", help="List reasoning modes and plan contract")
    plans.set_defaults(func=cmd_plans)


def _digest(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]
