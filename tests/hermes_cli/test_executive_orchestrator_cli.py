from __future__ import annotations

import json
import time

from gateway.executive_orchestrator import (
    ExecutiveOrchestrator,
    InMemoryExecutiveTraceSink,
    NoopExecutiveContextProvider,
)
from hermes_cli.executive_orchestrator import (
    executive_orchestrator_status,
    lookup_executive_traces,
    run_local_diagnostic_turn,
)


class FakeDiagnosticAgent:
    provider = "custom"
    model = "gpt-4.1-mini"

    def __init__(self) -> None:
        self.calls = []
        self.closed = False

    def run_conversation(self, message, **kwargs):  # noqa: ANN001
        self.calls.append((message, kwargs))
        return {"final_response": "diagnostic healthy"}

    def close(self) -> None:
        self.closed = True


def test_status_is_operator_safe_and_non_executing(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED", "true")

    status = executive_orchestrator_status()

    assert status["enabled"] is True
    assert status["execution_boundary"] == "not_executed"
    assert status["live_execution_enabled"] is False
    assert status["diagnostic_ingress"] == "local_cli_only"
    assert status["outbound_platform_delivery"] is False


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
    assert agent.closed is True
    assert len(agent.calls) == 1
    assert "EXECUTIVE ORCHESTRATOR CONTEXT" in agent.calls[0][0]


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
