from __future__ import annotations

from gateway.executive_orchestrator import (
    ExecutiveOrchestrator,
    ExecutiveTurnInput,
    InMemoryExecutiveTraceSink,
    NoopExecutiveContextProvider,
    classify_request,
    run_reasoning_with_optional_orchestrator,
)


class RecordingAgent:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[object, dict]] = []

    def run_conversation(self, message, **kwargs):  # noqa: ANN001
        self.calls.append((message, kwargs))
        return {"final_response": self.response}


def _turn(message: str, *, platform: str = "whatsapp") -> ExecutiveTurnInput:
    return ExecutiveTurnInput(
        tenant_id="tenant-1",
        conversation_id="conversation-1",
        actor_id="user-1",
        actor_name="Nitin",
        platform=platform,
        chat_id="chat-1",
        message=message,
        session_id="session-1",
        session_key=f"{platform}:chat-1:user-1",
    )


def test_whatsapp_response_sanitizer_removes_internal_architecture_details() -> None:
    agent = RecordingAgent(
        "GatewayRunner._handle_message calls ExecutiveOrchestrator.prepare_turn "
        "in /opt/ai-stack/hermes-agent/gateway/executive_orchestrator.py, "
        "trace_id=trace_123, commit e48afa71693dfbde08448b4a92e0038384773053."
    )

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message="Explain the full Hermes architecture.",
        conversation_kwargs={"conversation_history": [], "task_id": "session-1"},
        turn=_turn("Explain the full Hermes architecture."),
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=ExecutiveOrchestrator(
            context_provider=NoopExecutiveContextProvider(),
            trace_sink=InMemoryExecutiveTraceSink(),
        ),
    )

    response = result.result["final_response"]
    assert "GatewayRunner" not in response
    assert "ExecutiveOrchestrator" not in response
    assert "/opt/ai-stack" not in response
    assert "trace_" not in response
    assert "e48afa" not in response
    assert "Hermes gathers relevant information" in response
    assert result.result["executive_orchestrator"]["disclosure_class"] == "user_safe"
    assert (
        "ip_disclosure_sanitized" in result.result["executive_orchestrator"]["warnings"]
    )


def test_self_improvement_channel_output_is_quarantined_as_proposal_only() -> None:
    agent = RecordingAgent(
        "💾 Self-improvement review: User profile updated. "
        "Skill 'calendar-decision-planner' updated (full rewrite)."
    )

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message="Thanks",
        conversation_kwargs={"conversation_history": [], "task_id": "session-1"},
        turn=_turn("Thanks"),
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=ExecutiveOrchestrator(
            context_provider=NoopExecutiveContextProvider(),
            trace_sink=InMemoryExecutiveTraceSink(),
        ),
    )

    response = result.result["final_response"]
    assert "Self-improvement review" not in response
    assert "User profile updated" not in response
    assert "Skill" not in response
    proposal = result.result["executive_orchestrator"]["improvement_proposal"]
    assert proposal["review_status"] == "proposed"
    assert proposal["approval_status"] == "not_requested"
    assert proposal["application_status"] == "not_applied"


def test_capability_truth_plain_language_for_unavailable_capabilities() -> None:
    agent = RecordingAgent(
        "Calendar adapter unavailable because execution_boundary=not_executed; "
        "Google Calendar authorisation status is configured_awaiting_live_read_enablement."
    )

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message="Which Google Calendar account is connected?",
        conversation_kwargs={"conversation_history": [], "task_id": "session-1"},
        turn=_turn("Which Google Calendar account is connected?"),
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=ExecutiveOrchestrator(
            context_provider=NoopExecutiveContextProvider(),
            trace_sink=InMemoryExecutiveTraceSink(),
        ),
    )

    response = result.result["final_response"]
    assert response == "No Google Calendar account is currently authorised."
    assert "adapter" not in response.casefold()
    assert "execution_boundary" not in response
    assert (
        result.result["executive_orchestrator"]["capability_truth"]["enabled"] is True
    )


def test_planning_discussion_is_not_execution_classification() -> None:
    assert (
        classify_request("Create a decision plan comparing Calendar and Gmail.")
        == "planning_request"
    )
    assert (
        classify_request(
            "Compare Calendar and Gmail for the lowest-risk first connector."
        )
        == "decision_support"
    )
    assert classify_request("Connect Calendar now.") == "potentially_executable"
    assert classify_request("Read my Calendar tomorrow.") == "potentially_executable"
