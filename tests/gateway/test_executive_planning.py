from __future__ import annotations

import json

import pytest

from gateway.executive_orchestrator import (
    ExecutiveOrchestrator,
    ExecutiveTurnInput,
    InMemoryExecutiveTraceSink,
    NoopExecutiveContextProvider,
    run_reasoning_with_optional_orchestrator,
)
from gateway.executive_reasoning import (
    ReasoningPlanningRequest,
    build_default_reasoning_engine,
)


class RecordingAgent:
    provider = "custom"
    model = "gpt-4.1-mini"

    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def run_conversation(self, message: object, **kwargs: object) -> dict[str, object]:
        self.calls.append((message, kwargs))
        return {"final_response": "Planning response."}


def _turn(message: str = "Help me plan the next milestone.") -> ExecutiveTurnInput:
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


def _reasoning_plan(message: str = "Help me plan the next milestone.") -> object:
    return build_default_reasoning_engine().plan(
        ReasoningPlanningRequest(
            correlation_id="eo_plan_test",
            tenant_id="tenant-1",
            actor_id="user-1",
            normalized_user_request=message,
            request_classification="planning_request",
            context_source_counts={"persistent_profile": 1, "recent_conversation": 2},
            evidence_refs=("profile-1", "recent-1"),
            safety_state="execution_unavailable_not_executed",
            trace_metadata={},
        )
    )


def test_planning_contract_rejects_any_executable_terminal_state() -> None:
    from gateway.executive_planning import ExecutivePlan, PlanObjective

    with pytest.raises(ValueError, match="plan_status"):
        ExecutivePlan(
            plan_id="plan_bad",
            planning_request_id="epr_bad",
            strategy_id="milestone_plan",
            objective=PlanObjective(
                objective_id="objective-1",
                summary="Plan the milestone.",
            ),
            plan_status="approved",
        )

    with pytest.raises(ValueError, match="execution_status"):
        ExecutivePlan(
            plan_id="plan_bad",
            planning_request_id="epr_bad",
            strategy_id="milestone_plan",
            objective=PlanObjective(
                objective_id="objective-1",
                summary="Plan the milestone.",
            ),
            execution_status="executed",
        )


def test_default_registry_lists_only_enabled_deterministic_strategies() -> None:
    from gateway.executive_planning import build_default_planning_registry

    registry = build_default_planning_registry()

    assert registry.strategy_ids() == (
        "decision_plan",
        "implementation_plan",
        "milestone_plan",
        "review_plan",
    )
    assert registry.lookup("milestone_plan").deterministic is True
    assert registry.lookup("milestone_plan").lifecycle_state == "enabled"
    assert registry.lookup("milestone_plan").execution_supported is False
    assert registry.lookup("milestone_plan").external_calls_enabled is False


def test_planning_policy_allows_only_safe_reasoning_planning_stub() -> None:
    from gateway.executive_planning import ExecutivePlanningRequest, PlanningPolicy

    plan = _reasoning_plan()
    request = ExecutivePlanningRequest.from_reasoning_plan(
        reasoning_plan=plan,
        normalized_user_request="Help me plan the next milestone.",
        tenant_id="tenant-1",
        actor_id="user-1",
        context_source_counts={"persistent_profile": 1},
        evidence_refs=("profile-1",),
        trace_metadata={},
    )

    decision = PlanningPolicy().evaluate(request)

    assert decision.eligible is True
    assert decision.reason_code == "planning_stub_eligible"

    unsafe = ExecutivePlanningRequest.from_reasoning_plan(
        reasoning_plan=plan,
        normalized_user_request="Send an email after planning.",
        tenant_id="tenant-1",
        actor_id="user-1",
        context_source_counts={},
        evidence_refs=(),
        trace_metadata={},
        safety_state="execution_unavailable_not_executed",
    )
    blocked = PlanningPolicy().evaluate(unsafe)

    assert blocked.eligible is False
    assert blocked.reason_code == "external_action_not_plannable_without_approval"


def test_planning_engine_produces_bounded_proposals_only() -> None:
    from gateway.executive_planning import (
        build_default_planning_engine,
        ExecutivePlanningRequest,
    )

    request = ExecutivePlanningRequest.from_reasoning_plan(
        reasoning_plan=_reasoning_plan(),
        normalized_user_request="Help me plan the next milestone without starting connectors yet.",
        tenant_id="tenant-1",
        actor_id="user-1",
        context_source_counts={"persistent_profile": 1, "recent_conversation": 2},
        evidence_refs=("profile-1", "recent-1"),
        trace_metadata={"executive_intelligence_snapshot": {"signal_count": 2}},
    )

    snapshot = build_default_planning_engine().plan(request)
    plan = snapshot.recommended_plan

    assert snapshot.status == "proposed"
    assert snapshot.execution_status == "not_executed"
    assert snapshot.approval_status == "not_requested"
    assert plan is not None
    assert plan.plan_status == "proposed"
    assert plan.approval_status == "not_requested"
    assert plan.execution_status == "not_executed"
    assert 1 <= len(snapshot.candidate_plans) <= 3
    assert len(plan.steps) <= 30
    assert all(step.execution_status == "not_executed" for step in plan.steps)
    assert all(step.status == "proposed" for step in plan.steps)
    assert plan.recommendation is not None
    assert plan.recommendation.approval_status == "not_requested"
    assert plan.recommendation.execution_status == "not_executed"
    assert "not approved or executed" in plan.recommendation.rationale.casefold()
    rendered = json.dumps(snapshot.safe_trace()).casefold()
    assert "secret" not in rendered
    assert "token" not in rendered


def test_planning_engine_keeps_external_actions_as_descriptive_references() -> None:
    from gateway.executive_planning import (
        build_default_planning_engine,
        ExecutivePlanningRequest,
    )

    message = "Plan how we would create a ClickUp task tomorrow, but do not execute."
    request = ExecutivePlanningRequest.from_reasoning_plan(
        reasoning_plan=_reasoning_plan(message),
        normalized_user_request=message,
        tenant_id="tenant-1",
        actor_id="user-1",
        context_source_counts={"current_request_metadata": 1},
        evidence_refs=("current-1",),
        trace_metadata={},
    )

    snapshot = build_default_planning_engine().plan(request)
    plan = snapshot.recommended_plan

    assert plan is not None
    assert plan.proposed_actions
    assert all(
        action.execution_status == "not_executed" for action in plan.proposed_actions
    )
    assert all(
        action.approval_status == "not_requested" for action in plan.proposed_actions
    )
    assert all(action.adapter_id is None for action in plan.proposed_actions)
    assert all(action.external_payload is None for action in plan.proposed_actions)
    assert "clickup" in plan.proposed_actions[0].action_type


def test_planning_dependency_validation_rejects_missing_and_circular_dependencies() -> (
    None
):
    from gateway.executive_planning import (
        ExecutivePlan,
        PlanDependency,
        PlanObjective,
        PlanStep,
        validate_plan_dependencies,
    )

    missing = ExecutivePlan(
        plan_id="plan_missing",
        planning_request_id="epr_missing",
        strategy_id="milestone_plan",
        objective=PlanObjective(objective_id="objective-1", summary="Plan safely."),
        steps=(PlanStep(step_id="step-1", title="One", sequence=1),),
        dependencies=(
            PlanDependency(
                dependency_id="dep-1", predecessor_id="missing", successor_id="step-1"
            ),
        ),
    )
    assert validate_plan_dependencies(missing)[0].code == "missing_dependency_reference"

    circular = ExecutivePlan(
        plan_id="plan_cycle",
        planning_request_id="epr_cycle",
        strategy_id="milestone_plan",
        objective=PlanObjective(objective_id="objective-1", summary="Plan safely."),
        steps=(
            PlanStep(step_id="step-1", title="One", sequence=1),
            PlanStep(step_id="step-2", title="Two", sequence=2),
        ),
        dependencies=(
            PlanDependency(
                dependency_id="dep-1", predecessor_id="step-1", successor_id="step-2"
            ),
            PlanDependency(
                dependency_id="dep-2", predecessor_id="step-2", successor_id="step-1"
            ),
        ),
    )
    assert validate_plan_dependencies(circular)[0].code == "circular_dependency"


def test_orchestrator_includes_planning_snapshot_for_eligible_turns(
    monkeypatch,
) -> None:
    monkeypatch.setenv("HERMES_PLANNING_ENGINE_ENABLED", "true")
    sink = InMemoryExecutiveTraceSink()
    orchestrator = ExecutiveOrchestrator(
        context_provider=NoopExecutiveContextProvider(),
        trace_sink=sink,
    )
    agent = RecordingAgent()

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message="Help me plan the next milestone without starting connectors yet.",
        conversation_kwargs={"conversation_history": [], "task_id": "session-1"},
        turn=_turn("Help me plan the next milestone without starting connectors yet."),
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=orchestrator,
    )

    assert result.prepared is not None
    prompt = str(agent.calls[0][0])
    assert "EXECUTIVE PLANNING SNAPSHOT" in prompt
    meta = dict(result.result["executive_orchestrator"])  # type: ignore[index]
    planning = meta["planning_snapshot"]
    assert planning["status"] == "proposed"
    assert planning["strategy_id"] == "milestone_plan"
    assert planning["execution_status"] == "not_executed"
    assert planning["approval_status"] == "not_requested"
    requested = next(
        record for record in sink.records if record["stage"] == "reasoning_requested"
    )
    assert requested["planning_snapshot"]["execution_status"] == "not_executed"


def test_orchestrator_bypasses_planning_for_simple_conversation(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_PLANNING_ENGINE_ENABLED", "true")
    agent = RecordingAgent()

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message="Hello Hermes.",
        conversation_kwargs={"conversation_history": [], "task_id": "session-1"},
        turn=_turn("Hello Hermes."),
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=ExecutiveOrchestrator(
            context_provider=NoopExecutiveContextProvider(),
            trace_sink=InMemoryExecutiveTraceSink(),
        ),
    )

    assert "EXECUTIVE PLANNING SNAPSHOT" not in str(agent.calls[0][0])
    assert (
        result.result["executive_orchestrator"]["planning_snapshot"]["status"]
        == "not_eligible"
    )
