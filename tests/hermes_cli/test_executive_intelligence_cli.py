from __future__ import annotations

import json

from hermes_cli.executive_intelligence import (
    intelligence_diagnostics,
    intelligence_modules,
    intelligence_status,
)


def test_intelligence_status_is_operator_safe_and_non_executing(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_INTELLIGENCE_ENABLED", "true")
    monkeypatch.setenv("HERMES_INFERENCE_INTELLIGENCE_MODULES_ENABLED", "false")

    status = intelligence_status()
    rendered = json.dumps(status).casefold()

    assert status["enabled"] is True
    assert status["registry_enabled"] is True
    assert status["deterministic_modules_enabled"] is True
    assert status["inference_modules_enabled"] is False
    assert status["external_calls_enabled"] is False
    assert status["live_execution_enabled"] is False
    assert status["execution_boundary"] == "not_executed"
    assert status["enabled_module_count"] >= 7
    assert "secret" not in rendered
    assert "token" not in rendered


def test_intelligence_modules_lists_deterministic_modules_without_payloads() -> None:
    modules = intelligence_modules()
    module_ids = [module["module_id"] for module in modules["modules"]]

    assert "schedule_summary" in module_ids
    assert "calendar_conflict" in module_ids
    assert "context_availability" in module_ids
    assert all(module["deterministic"] is True for module in modules["modules"])
    assert modules["inference_modules_enabled"] is False


def test_intelligence_diagnostics_runs_synthetic_non_external_probe() -> None:
    diagnostics = intelligence_diagnostics()

    assert diagnostics["status"] == "ok"
    assert diagnostics["external_calls_enabled"] is False
    assert diagnostics["live_execution_enabled"] is False
    assert diagnostics["execution_boundary"] == "not_executed"
    assert diagnostics["snapshot"]["signal_count"] >= 1
    assert "meeting_count" in diagnostics["snapshot"]["signal_counts_by_type"]
