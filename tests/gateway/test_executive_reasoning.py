from __future__ import annotations

import json

from gateway.executive_context_providers import (
    ContextEvidenceReference,
    ExecutiveContextContribution,
    ExecutiveContextSnapshot,
)
from gateway.executive_orchestrator import (
    ContextItem,
    ExecutiveOrchestrator,
    ExecutiveTurnInput,
    InMemoryExecutiveTraceSink,
    NoopExecutiveContextProvider,
    run_reasoning_with_optional_orchestrator,
)
from gateway.executive_reasoning import (
    ConfidenceLevel,
    EvidenceNeed,
    ReasoningPlan,
    ReasoningPlanningRequest,
    ResponsePlan,
    build_default_reasoning_engine,
    build_default_reasoning_mode_registry,
    build_reasoning_status,
    is_ai_provider_selection_enabled,
    is_executive_reasoning_engine_enabled,
    is_planning_engine_enabled,
    is_reasoning_planner_enabled,
    is_skill_selection_enabled,
)


class RecordingAgent:
    provider = "custom"
    model = "gpt-4.1-mini"

    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def run_conversation(self, message: object, **kwargs: object) -> dict[str, object]:
        self.calls.append((message, kwargs))
        return {"final_response": "Recorded response."}


def _turn(message: str) -> ExecutiveTurnInput:
    return ExecutiveTurnInput(
        tenant_id="tenant-1",
        conversation_id="conversation-1",
        actor_id="user-1",
        actor_name="Nitin",
        platform="local_diagnostic",
        chat_id=None,
        message=message,
        session_id="session-1",
        session_key="session-1",
    )


def _snapshot(*, context_type: str = "meeting") -> ExecutiveContextSnapshot:
    evidence = ContextEvidenceReference(
        evidence_id="evidence-1",
        source_provider_id="provider-1",
        source_mechanism="synthetic_test",
        source_record_ref="record-1",
        observed_at="2026-07-29T10:00:00Z",
        digest="digest-1",
    )
    contribution = ExecutiveContextContribution(
        contribution_id="contribution-1",
        context_type=context_type,
        title="Synthetic evidence",
        summary="Synthetic bounded evidence.",
        payload={"trace_category": context_type},
        source_provider_id="provider-1",
        source_mechanism="synthetic_test",
        source_record_ref="record-1",
        observed_at="2026-07-29T10:00:00Z",
        tenant_id="tenant-1",
        user_id="user-1",
        evidence_refs=(evidence,),
    )
    return ExecutiveContextSnapshot(
        tenant_id="tenant-1",
        user_id="user-1",
        request_classification="executive_status",
        contributions=(contribution,),
        selected_provider_ids=("provider-1",),
        successful_provider_ids=("provider-1",),
        failed_provider_ids=(),
        provider_trace={},
        warnings=(),
        total_collection_latency_ms=0,
        composed_context="Synthetic bounded evidence.",
        context_digest="context-digest",
        snapshot_digest="snapshot-digest",
    )


def test_reasoning_contracts_are_declarative_and_non_executing() -> None:
    evidence = EvidenceNeed(
        evidence_type="schedule_context",
        source_category="calendar_context",
        required=True,
        available=False,
        evidence_refs=(),
        limitation="Calendar live reads are disabled.",
    )
    plan = ReasoningPlan(
        plan_id="rp_test",
        correlation_id="eo_test",
        request_classification="executive_status",
        reasoning_mode="question_answering",
        user_objective="Answer schedule availability from known data.",
        sub_questions=("What schedule context is available?",),
        evidence_needs=(evidence,),
        confidence_by_claim={"meeting_data": ConfidenceLevel.UNAVAILABLE},
        missing_information=("Calendar live reads are disabled.",),
        selected_skills=(),
        selected_provider="standard_conversational_model",
        safety_state="normal_non_executing",
    )
    response_plan = ResponsePlan.from_reasoning_plan(plan)

    assert plan.execution_required is False
    assert plan.execution_permitted is False
    assert response_plan.execution_required is False
    assert response_plan.execution_permitted is False
    assert response_plan.safety_state == "normal_non_executing"
    assert response_plan.limitations == ("Calendar live reads are disabled.",)


def test_mode_registry_contains_initial_reasoning_modes() -> None:
    registry = build_default_reasoning_mode_registry()

    assert set(registry.mode_ids()) >= {
        "direct_answer",
        "executive_summary",
        "executive_brief",
        "analysis",
        "comparison",
        "planning_stub",
        "review",
        "explanation",
        "question_answering",
    }


def test_reasoning_engine_builds_missing_evidence_plan_for_meetings() -> None:
    engine = build_default_reasoning_engine()
    plan = engine.plan(
        ReasoningPlanningRequest(
            correlation_id="eo_meetings",
            tenant_id="tenant-1",
            actor_id="user-1",
            normalized_user_request="What meetings do I have today?",
            request_classification="executive_status",
            context_source_counts={"current_request_metadata": 1},
            evidence_refs=(),
            safety_state="normal_non_executing",
            trace_metadata={},
        )
    )

    assert plan.reasoning_mode == "question_answering"
    assert plan.evidence_needs[0].source_category == "calendar_context"
    assert plan.evidence_needs[0].available is False
    assert plan.confidence_by_claim["schedule_context"] == ConfidenceLevel.UNAVAILABLE
    assert "Do not infer meetings without meeting evidence." in plan.constraints
    assert plan.execution_permitted is False


def test_reasoning_engine_selects_planning_stub_without_executing_skills() -> None:
    engine = build_default_reasoning_engine()
    plan = engine.plan(
        ReasoningPlanningRequest(
            correlation_id="eo_plan",
            tenant_id="tenant-1",
            actor_id="user-1",
            normalized_user_request="Help me plan the next milestone without starting connectors yet.",
            request_classification="planning_request",
            context_source_counts={"daily_brief": 1},
            evidence_refs=("brief-1",),
            safety_state="execution_unavailable_not_executed",
            trace_metadata={},
        )
    )

    assert plan.reasoning_mode == "planning_stub"
    assert plan.selected_skills == ("milestone_planning",)
    assert plan.skill_execution == "selected_not_executed"
    assert plan.execution_required is False
    assert plan.execution_permitted is False


def test_reasoning_engine_is_repeatable_and_does_not_call_integrations() -> None:
    engine = build_default_reasoning_engine()
    request = ReasoningPlanningRequest(
        correlation_id="eo_repeat",
        tenant_id="tenant-1",
        actor_id="user-1",
        normalized_user_request="Should we add read-only Gmail first or stabilise WhatsApp behaviour first?",
        request_classification="decision_support",
        context_source_counts={"executive_intelligence": 1},
        evidence_refs=("intel-1",),
        safety_state="normal_non_executing",
        trace_metadata={"integration_service": object()},
    )

    first = engine.plan(request)
    second = engine.plan(request)

    assert first.safe_trace() == second.safe_trace()
    assert first.reasoning_mode == "comparison"
    assert first.selected_provider == "reasoning_model"
    assert first.external_calls_enabled is False


def test_orchestrator_adds_response_plan_to_reasoning_context_and_trace() -> None:
    sink = InMemoryExecutiveTraceSink()
    orchestrator = ExecutiveOrchestrator(
        context_provider=NoopExecutiveContextProvider(),
        trace_sink=sink,
    )
    agent = RecordingAgent()

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message="What meetings do I have today?",
        conversation_kwargs={"conversation_history": [], "task_id": "session-1"},
        turn=_turn("What meetings do I have today?"),
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=orchestrator,
    )

    assert result.prepared is not None
    reasoning_message = str(agent.calls[0][0])
    assert "EXECUTIVE REASONING PLAN" in reasoning_message
    assert "Do not infer meetings without meeting evidence." in reasoning_message
    meta = dict(result.result["executive_orchestrator"])  # type: ignore[index]
    assert meta["reasoning_plan"]["reasoning_mode"] == "question_answering"
    assert meta["response_plan"]["selected_model"] == "standard_conversational_model"
    assert meta["execution_state"] == "not_executed"
    requested = next(
        record for record in sink.records if record["stage"] == "reasoning_requested"
    )
    assert requested["reasoning_plan"]["execution_permitted"] is False
    assert requested["response_plan"]["execution_permitted"] is False


def test_reasoning_plan_uses_traceable_context_and_never_invents_evidence() -> None:
    engine = build_default_reasoning_engine()
    snapshot = _snapshot(context_type="meeting")
    plan = engine.plan(
        ReasoningPlanningRequest(
            correlation_id="eo_context",
            tenant_id="tenant-1",
            actor_id="user-1",
            normalized_user_request="What meetings do I have today?",
            request_classification="executive_status",
            context_source_counts=snapshot.contribution_counts_by_type,
            evidence_refs=("record-1",),
            safety_state="normal_non_executing",
            trace_metadata={
                "executive_context_snapshot": snapshot.safe_trace_metadata()
            },
        )
    )

    assert plan.evidence_needs[0].available is True
    assert plan.evidence_needs[0].evidence_refs == ("record-1",)
    assert plan.confidence_by_claim["schedule_context"] == ConfidenceLevel.KNOWN


def test_reasoning_status_flags_default_safe_rollout(monkeypatch) -> None:
    monkeypatch.delenv("HERMES_PLANNING_ENGINE_ENABLED", raising=False)
    monkeypatch.delenv("HERMES_LIVE_EXECUTION_ENABLED", raising=False)
    monkeypatch.setenv("HERMES_EXECUTIVE_REASONING_ENGINE_ENABLED", "true")

    status = build_reasoning_status()

    assert is_executive_reasoning_engine_enabled() is True
    assert is_reasoning_planner_enabled() is True
    assert is_skill_selection_enabled() is True
    assert is_ai_provider_selection_enabled() is True
    assert is_planning_engine_enabled() is True
    assert status["execution_boundary"] == "not_executed"
    assert status["live_execution_enabled"] is False
    assert status["external_calls_enabled"] is False
    assert "secret" not in json.dumps(status).casefold()
