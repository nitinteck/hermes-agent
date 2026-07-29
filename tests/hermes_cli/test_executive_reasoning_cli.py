from __future__ import annotations

import json

from hermes_cli.executive_reasoning import (
    reasoning_diagnostics,
    reasoning_plans,
    reasoning_status,
)


def test_reasoning_status_is_operator_safe_and_non_executing(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_REASONING_ENGINE_ENABLED", "true")
    monkeypatch.delenv("HERMES_PLANNING_ENGINE_ENABLED", raising=False)

    status = reasoning_status()
    rendered = json.dumps(status).casefold()

    assert status["enabled"] is True
    assert status["reasoning_planner_enabled"] is True
    assert status["skill_selection_enabled"] is True
    assert status["ai_provider_selection_enabled"] is True
    assert status["planning_engine_enabled"] is False
    assert status["execution_boundary"] == "not_executed"
    assert status["live_execution_enabled"] is False
    assert status["external_calls_enabled"] is False
    assert "secret" not in rendered
    assert "token" not in rendered


def test_reasoning_diagnostics_returns_safe_plan_without_external_calls() -> None:
    diagnostics = reasoning_diagnostics()

    assert diagnostics["status"] == "ok"
    assert diagnostics["external_calls_enabled"] is False
    assert diagnostics["live_execution_enabled"] is False
    assert diagnostics["execution_boundary"] == "not_executed"
    assert diagnostics["reasoning_plan"]["execution_permitted"] is False
    assert diagnostics["response_plan"]["execution_permitted"] is False
    assert diagnostics["reasoning_plan"]["reasoning_mode"] == "question_answering"
    assert diagnostics["redacted"] is True


def test_reasoning_plans_lists_modes_and_confidence_model() -> None:
    plans = reasoning_plans()
    mode_ids = {mode["mode_id"] for mode in plans["modes"]}

    assert "planning_stub" in mode_ids
    assert "comparison" in mode_ids
    assert "question_answering" in mode_ids
    assert plans["skill_execution"] == "selected_not_executed"
    assert plans["execution_boundary"] == "not_executed"
    assert set(plans["confidence_levels"]) == {
        "known",
        "derived",
        "assumed",
        "unavailable",
        "conflicting",
        "unknown",
    }
