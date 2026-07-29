"""Operator-safe Executive Planning Engine diagnostics."""

from __future__ import annotations

import json
from typing import Any

from gateway.executive_planning import (
    ExecutivePlanningRequest,
    build_default_planning_engine,
    build_default_planning_registry,
    build_planning_status,
)
from gateway.executive_reasoning import (
    ReasoningPlanningRequest,
    build_default_reasoning_engine,
)


def planning_status() -> dict[str, Any]:
    return build_planning_status()


def planning_strategies() -> dict[str, Any]:
    registry = build_default_planning_registry()
    return {
        "status": "ok",
        "external_calls_enabled": False,
        "execution_boundary": "not_executed",
        "strategies": [
            registry.lookup(strategy_id).safe_trace()
            for strategy_id in registry.strategy_ids()
        ],
        "redacted": True,
    }


def planning_diagnostics() -> dict[str, Any]:
    reasoning = build_default_reasoning_engine().plan(
        ReasoningPlanningRequest(
            correlation_id="eo_planning_diagnostic",
            tenant_id="diagnostic-tenant",
            actor_id="diagnostic-user",
            normalized_user_request=(
                "Help me plan the next milestone without starting connectors yet."
            ),
            request_classification="planning_request",
            context_source_counts={"current_request_metadata": 1},
            evidence_refs=("current_request:diagnostic",),
            safety_state="execution_unavailable_not_executed",
            trace_metadata={"diagnostic": True},
        )
    )
    snapshot = build_default_planning_engine().plan(
        ExecutivePlanningRequest.from_reasoning_plan(
            reasoning_plan=reasoning,
            normalized_user_request=(
                "Help me plan the next milestone without starting connectors yet."
            ),
            tenant_id="diagnostic-tenant",
            actor_id="diagnostic-user",
            context_source_counts={"current_request_metadata": 1},
            evidence_refs=("current_request:diagnostic",),
            trace_metadata={"diagnostic": True},
        )
    )
    return {
        "status": "ok",
        "external_calls_enabled": False,
        "live_execution_enabled": False,
        "execution_boundary": "not_executed",
        "planning_snapshot": snapshot.safe_trace(),
        "rendered_plan_digest": _digest(json.dumps(snapshot.safe_trace())),
        "redacted": True,
    }


def planning_plans() -> dict[str, Any]:
    return {
        "status": "ok",
        "storage_mode": "request_scoped",
        "durable_plan_persistence_enabled": False,
        "approval_status": "not_requested",
        "execution_status": "not_executed",
        "plans": [],
        "redacted": True,
    }


def cmd_status(args: Any) -> None:
    del args
    print(json.dumps(planning_status(), sort_keys=True))


def cmd_strategies(args: Any) -> None:
    del args
    print(json.dumps(planning_strategies(), sort_keys=True))


def cmd_diagnostics(args: Any) -> None:
    del args
    print(json.dumps(planning_diagnostics(), sort_keys=True))


def cmd_plans(args: Any) -> None:
    del args
    print(json.dumps(planning_plans(), sort_keys=True))


def register_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "planning",
        help="Inspect Executive Planning Engine state",
    )
    parser.set_defaults(func=cmd_status)
    subs = parser.add_subparsers(dest="planning_command")
    status = subs.add_parser("status", help="Show Executive Planning status")
    status.set_defaults(func=cmd_status)
    strategies = subs.add_parser(
        "strategies",
        help="List deterministic planning strategies",
    )
    strategies.set_defaults(func=cmd_strategies)
    diagnostics = subs.add_parser(
        "diagnostics",
        help="Run a synthetic non-executing planning diagnostic",
    )
    diagnostics.set_defaults(func=cmd_diagnostics)
    plans = subs.add_parser(
        "plans",
        help="List request-scoped proposed plans retained by the CLI",
    )
    plans.set_defaults(func=cmd_plans)


def _digest(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]
