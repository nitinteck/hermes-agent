from __future__ import annotations

from gateway.executive_orchestrator import (
    ExecutiveOrchestrator,
    InMemoryExecutiveTraceSink,
    NoopExecutiveContextProvider,
)
from hermes_cli.executive_orchestrator import (
    executive_orchestrator_status,
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
