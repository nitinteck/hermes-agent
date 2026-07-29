from __future__ import annotations

import json

from hermes_cli.executive_planning import (
    planning_diagnostics,
    planning_plans,
    planning_status,
    planning_strategies,
)


def test_planning_status_is_operator_safe_and_non_executing(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_PLANNING_ENGINE_ENABLED", "true")
    monkeypatch.delenv("HERMES_PLANNING_MODEL_ASSISTED_ENABLED", raising=False)

    status = planning_status()
    rendered = json.dumps(status).casefold()

    assert status["enabled"] is True
    assert status["registry_enabled"] is True
    assert status["deterministic_planning_enabled"] is True
    assert status["model_assisted_planning_enabled"] is False
    assert status["candidate_evaluation_enabled"] is True
    assert status["proposed_action_generation_enabled"] is True
    assert status["approval_engine_enabled"] is False
    assert status["execution_engine_enabled"] is False
    assert status["external_calls_enabled"] is False
    assert status["execution_boundary"] == "not_executed"
    assert status["execution_status"] == "not_executed"
    assert "secret" not in rendered
    assert "token" not in rendered


def test_planning_strategies_lists_deterministic_registry() -> None:
    strategies = planning_strategies()
    strategy_ids = {item["strategy_id"] for item in strategies["strategies"]}

    assert strategies["status"] == "ok"
    assert strategy_ids == {
        "milestone_plan",
        "implementation_plan",
        "decision_plan",
        "review_plan",
    }
    assert all(item["deterministic"] is True for item in strategies["strategies"])
    assert all(
        item["external_calls_enabled"] is False for item in strategies["strategies"]
    )


def test_planning_diagnostics_returns_proposed_not_executed_snapshot() -> None:
    diagnostics = planning_diagnostics()

    assert diagnostics["status"] == "ok"
    assert diagnostics["external_calls_enabled"] is False
    assert diagnostics["execution_boundary"] == "not_executed"
    assert diagnostics["planning_snapshot"]["status"] == "proposed"
    assert diagnostics["planning_snapshot"]["approval_status"] == "not_requested"
    assert diagnostics["planning_snapshot"]["execution_status"] == "not_executed"
    assert diagnostics["planning_snapshot"]["candidate_count"] >= 1
    assert diagnostics["planning_snapshot"]["recommended_plan_id"]
    assert diagnostics["redacted"] is True


def test_planning_plans_returns_request_scoped_synthetic_plans_only() -> None:
    plans = planning_plans()

    assert plans["status"] == "ok"
    assert plans["storage_mode"] == "request_scoped"
    assert plans["durable_plan_persistence_enabled"] is False
    assert plans["approval_status"] == "not_requested"
    assert plans["execution_status"] == "not_executed"
    assert plans["plans"] == []
