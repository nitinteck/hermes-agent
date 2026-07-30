from __future__ import annotations

from gateway.executive_planning import (
    ExecutivePlanningRequest,
    PlanningContextBinding,
    build_default_planning_engine,
    render_planning_snapshot_for_prompt,
)


def _request(
    message: str, *, trace_metadata: dict | None = None
) -> ExecutivePlanningRequest:
    return ExecutivePlanningRequest.from_reasoning_plan(
        reasoning_plan={
            "plan_id": "rp-test",
            "reasoning_mode": "planning_stub",
            "execution_permitted": False,
            "execution_required": False,
            "selected_skills": ["milestone_planning"],
            "skill_execution": "selected_not_executed",
        },
        normalized_user_request=message,
        tenant_id="tenant-1",
        actor_id="user-1",
        context_source_counts={"recent_conversation": 2, "current_request_metadata": 1},
        evidence_refs=("recent_conversation:1:abc",),
        trace_metadata=trace_metadata or {},
        safety_state="execution_unavailable_not_executed",
    )


def test_unsafe_execution_first_plan_is_repaired_before_presentation() -> None:
    snapshot = build_default_planning_engine().plan(
        _request(
            "Create a plan where we deploy live execution first, build approvals "
            "afterwards and add safety controls at the end."
        )
    )

    assert snapshot.eligible is True
    assert snapshot.recommended_plan is not None
    assert snapshot.recommended_plan.status == "proposed"
    assert snapshot.recommended_plan.approval_status == "not_requested"
    assert snapshot.recommended_plan.execution_status == "not_executed"
    assert any(error.code == "unsafe_execution_order" for error in snapshot.errors)
    assert any(error.code == "approval_dependency_missing" for error in snapshot.errors)
    rendered = render_planning_snapshot_for_prompt(snapshot)
    assert "safety-first corrected plan" in rendered.casefold()
    assert rendered.index("safety controls") < rendered.index("restricted pilot")


def test_active_calendar_context_binds_into_follow_on_plan() -> None:
    binding = PlanningContextBinding(
        active_subject="controlled read-only Google Calendar activation",
        current_objective="choose first read-only connector",
        prior_options=("Google Calendar", "Gmail"),
        prior_recommendation="Google Calendar first because it is lower risk",
        latest_constraint="Do not start Gmail or any writes.",
        conversation_turn_ids=("turn-1", "turn-2", "turn-3"),
        source_context_ids=("recent_conversation:1", "recent_conversation:2"),
    )

    snapshot = build_default_planning_engine().plan(
        _request(
            "Now give me a three-step proposed plan.",
            trace_metadata={"planning_context_binding": binding.safe_trace()},
        )
    )

    assert snapshot.eligible is True
    assert snapshot.recommended_plan is not None
    rendered = render_planning_snapshot_for_prompt(snapshot)
    assert "controlled read-only google calendar activation" in rendered.casefold()
    assert "Gmail" in rendered
    assert "generic" not in " ".join(snapshot.warnings).casefold()


def test_high_ambition_revenue_plan_surfaces_missing_evidence_and_low_confidence() -> (
    None
):
    snapshot = build_default_planning_engine().plan(
        _request(
            "Create a plan to reach £1 million monthly revenue across Om Vidya Group within 12 months."
        )
    )

    assert snapshot.eligible is True
    assert snapshot.recommended_plan is not None
    rendered = render_planning_snapshot_for_prompt(snapshot)
    for missing in (
        "current revenue baseline",
        "margins",
        "capacity",
        "conversion",
        "capital",
        "unit economics",
    ):
        assert missing in rendered.casefold()
    assert "strategic framework" in rendered.casefold()
    assert "confidence: low" in rendered.casefold()
