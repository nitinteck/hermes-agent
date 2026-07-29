from __future__ import annotations

import json
import time
from typing import Any

from gateway.executive_orchestrator import (
    ExecutiveOrchestrator,
    InMemoryExecutiveTraceSink,
    NoopExecutiveContextProvider,
)
from hermes_cli.executive_orchestrator import (
    executive_orchestrator_status,
    lookup_executive_traces,
    run_local_behavioural_pack,
    run_local_diagnostic_turn,
)


class FakeDiagnosticAgent:
    provider = "custom"
    model = "gpt-4.1-mini"

    def __init__(self) -> None:
        self.calls: list[tuple[Any, dict[str, Any]]] = []
        self.closed = False

    def run_conversation(self, message, **kwargs):  # noqa: ANN001
        self.calls.append((message, kwargs))
        return {"final_response": "diagnostic healthy"}

    def close(self) -> None:
        self.closed = True


def test_status_is_operator_safe_and_non_executing(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.delenv("HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED", raising=False)
    monkeypatch.delenv("HERMES_MCP_CONTEXT_ADAPTER_ENABLED", raising=False)
    monkeypatch.delenv("HERMES_GOOGLE_CALENDAR_TOKEN_FILE", raising=False)
    monkeypatch.setenv("HERMES_GOOGLE_CALENDAR_CONTEXT_PROVIDER_ENABLED", "true")
    monkeypatch.setenv("HERMES_GOOGLE_CALENDAR_LIVE_READS_ENABLED", "false")

    status = executive_orchestrator_status()

    assert status["enabled"] is True
    assert status["executive_context_provider_framework_enabled"] is True
    assert status["mock_executive_context_provider_enabled"] is False
    assert status["mcp_context_adapter_enabled"] is False
    assert status["execution_boundary"] == "not_executed"
    assert status["live_execution_enabled"] is False
    assert status["google_calendar_context_provider_enabled"] is True
    assert status["google_calendar_live_reads_enabled"] is False
    assert status["google_calendar_descriptions_enabled"] is False
    assert status["google_calendar_write_capability_enabled"] is False
    assert (
        status["google_calendar_authorisation_status"]
        == "configured_awaiting_live_read_enablement"
    )
    assert status["diagnostic_ingress"] == "local_cli_only"
    assert status["outbound_platform_delivery"] is False
    assert "TOKEN" not in json.dumps(status).upper()


def test_local_diagnostic_turn_uses_orchestrator_without_outbound_delivery(
    monkeypatch,
) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "true")
    agent = FakeDiagnosticAgent()
    orchestrator = ExecutiveOrchestrator(
        context_provider=NoopExecutiveContextProvider(),
        trace_sink=InMemoryExecutiveTraceSink(),
    )

    result = run_local_diagnostic_turn(
        "What is the executive status?",
        agent_factory=lambda: agent,
        orchestrator=orchestrator,
    )

    assert result["status"] == "ok"
    assert result["enabled"] is True
    assert result["local_only"] is True
    assert result["outbound_platform_delivery"] is False
    assert result["external_execution"] == "not_executed"
    assert result["classification"] == "executive_status"
    assert result["provider"] == "custom"
    assert result["model"] == "gpt-4.1-mini"
    assert result["response"] == "diagnostic healthy"
    assert result["correlation_id"].startswith("eo_")
    assert result["trace_id"].startswith("trace_")
    assert result["no_execution_confirmed"] is True
    assert (
        result["effective_configuration"][
            "executive_context_provider_framework_enabled"
        ]
        is True
    )
    assert (
        result["effective_configuration"]["mock_executive_context_provider_enabled"]
        is False
    )
    assert result["effective_configuration"]["mcp_context_adapter_enabled"] is False
    assert result["context_provider_snapshot"]["selected_provider_ids"] == [
        "current_request_metadata",
        "persistent_profile",
        "recent_conversation",
    ]
    assert agent.closed is True
    assert len(agent.calls) == 1
    assert "EXECUTIVE ORCHESTRATOR CONTEXT" in agent.calls[0][0]


def test_local_diagnostic_turn_fails_fast_when_orchestrator_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "false")
    called = False

    def build_agent():
        nonlocal called
        called = True
        return FakeDiagnosticAgent()

    result = run_local_diagnostic_turn(
        "Hermes diagnostic should not run",
        agent_factory=build_agent,
    )

    assert result["status"] == "invalid"
    assert result["enabled"] is False
    assert result["invalid_reason"] == "executive_orchestrator_disabled"
    assert result["effective_configuration"]["execution_boundary"] == "not_executed"
    assert result["external_execution"] == "not_executed"
    assert called is False


def test_local_diagnostic_turn_can_explicitly_cover_disabled_mode(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "false")
    agent = FakeDiagnosticAgent()

    result = run_local_diagnostic_turn(
        "Disabled-mode coverage",
        agent_factory=lambda: agent,
        allow_disabled=True,
    )

    assert result["status"] == "disabled"
    assert result["enabled"] is False
    assert agent.calls


def test_behavioural_pack_fails_fast_when_orchestrator_disabled(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "false")
    called = False

    def build_agent():
        nonlocal called
        called = True
        return FakeDiagnosticAgent()

    result = run_local_behavioural_pack(agent_factory=build_agent)

    assert result["status"] == "invalid"
    assert result["invalid_reason"] == "executive_orchestrator_disabled"
    assert result["effective_configuration"]["enabled"] is False
    assert result["effective_configuration"]["execution_boundary"] == "not_executed"
    assert result["results"] == []
    assert called is False


def test_behavioural_pack_uses_one_local_non_executing_session(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "true")
    pack_path = tmp_path / "pack.json"
    pack_path.write_text(
        json.dumps({
            "tests": [
                {
                    "test_id": "A1",
                    "exact_whatsapp_message": "Hello Hermes.",
                    "expected_request_classification": "ordinary_conversation",
                },
                {
                    "test_id": "I1",
                    "exact_whatsapp_message": "Based on our last two messages, what boundary are you maintaining?",
                    "expected_request_classification": "executive_status",
                },
            ]
        }),
        encoding="utf-8",
    )
    agent = FakeDiagnosticAgent()
    orchestrator = ExecutiveOrchestrator(
        context_provider=NoopExecutiveContextProvider(),
        trace_sink=InMemoryExecutiveTraceSink(),
    )

    result = run_local_behavioural_pack(
        pack_path=pack_path,
        agent_factory=lambda: agent,
        orchestrator=orchestrator,
    )

    assert result["status"] == "ok"
    assert result["local_only"] is True
    assert result["whatsapp_ingress_used"] is False
    assert result["outbound_platform_delivery"] is False
    assert result["external_execution"] == "not_executed"
    assert result["summary"]["classification_correct"] == 2
    assert result["summary"]["classification_total"] == 2
    assert result["summary"]["safety_pass"] is True
    assert len(result["results"]) == 2
    assert result["results"][1]["context_source_counts"]["recent_conversation"] == 2
    assert result["results"][1]["execution_state"] == "not_executed"
    assert result["results"][1]["message_digest"]
    assert result["results"][1]["response_digest"]
    assert agent.calls[1][1]["conversation_history"]
    dumped = json.dumps(result)
    assert "local-diagnostic-operator" not in dumped


def test_trace_lookup_returns_redacted_classification_and_safety_state(
    tmp_path,
) -> None:
    trace_path = tmp_path / "executive_orchestrator_traces.jsonl"
    now = int(time.time())
    trace_path.write_text(
        "\n".join([
            json.dumps({
                "classification": "executive_status",
                "context_digest": "ctx123",
                "context_source_counts": {"daily_brief": 1, "journal": 2},
                "correlation_id": "eo_safe",
                "event_id": "event_1",
                "execution_state": "not_executed",
                "message_digest": "abc123456789",
                "provider": "custom",
                "model": "gpt-4.1-mini",
                "recorded_at": now,
                "response_digest": "def987654321",
                "safety_state": "normal_non_executing",
                "stage": "reasoning_completed",
                "status": "completed",
                "trace_id": "trace_safe",
            }),
            json.dumps({
                "classification": "ordinary_conversation",
                "correlation_id": "eo_other",
                "execution_state": "not_executed",
                "recorded_at": now,
                "stage": "reasoning_completed",
                "status": "completed",
                "trace_id": "trace_other",
                "private_message": "API_KEY=sk-should-not-appear",
            }),
        ])
        + "\n",
        encoding="utf-8",
    )

    result = lookup_executive_traces(
        trace_path=trace_path,
        message_digest="abc123",
        response_digest="def987",
    )

    dumped = json.dumps(result)
    assert result["status"] == "ok"
    assert result["redacted"] is True
    assert len(result["matches"]) == 1
    match = result["matches"][0]
    assert match["classification"] == "executive_status"
    assert match["safety_state"] == "normal_non_executing"
    assert match["execution_state"] == "not_executed"
    assert match["context_source_counts"] == {"daily_brief": 1, "journal": 2}
    assert "sk-should-not-appear" not in dumped
    assert "private_message" not in dumped
