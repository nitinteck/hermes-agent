from __future__ import annotations

import json

import pytest

from gateway.executive_context_providers import (
    ContextEvidenceReference,
    ExecutiveContextContribution,
    ExecutiveContextSnapshot,
)
from gateway.executive_context_repository import (
    ExecutiveContextRecord,
    ExecutiveContextResolver,
    InMemoryExecutiveContextRepository,
)
from gateway.executive_intelligence import (
    BackToBackLoadModule,
    CommitmentDueModule,
    ContextAvailabilityModule,
    ExecutiveIntelligenceEngine,
    ExecutiveIntelligenceSignal,
    FocusTimeModule,
    IntelligenceErrorCode,
    IntelligenceEvidenceReference,
    IntelligenceModuleDefinition,
    IntelligenceRegistry,
    IntelligenceScore,
    IntelligenceSelectionRequest,
    PreparationGapModule,
    ScheduleConflictModule,
    ScheduleSummaryModule,
    build_default_intelligence_engine,
    render_intelligence_snapshot_for_reasoning,
)
from gateway.executive_orchestrator import (
    ExecutiveContextLimits,
    ExecutiveOrchestrator,
    ExecutiveTurnInput,
    InMemoryExecutiveTraceSink,
    run_reasoning_with_optional_orchestrator,
)


TENANT = "tenant-1"
USER = "user-1"
NOW = "2026-07-29T08:00:00+01:00"


def _evidence(ref: str = "ctx-1") -> ContextEvidenceReference:
    return ContextEvidenceReference(
        evidence_id=f"evidence:{ref}",
        source_provider_id="synthetic_context",
        source_mechanism="synthetic_acceptance_fixture",
        source_record_ref=ref,
        observed_at="2026-07-29T07:55:00Z",
        digest=f"digest-{ref}",
    )


def _contribution(
    context_type: str,
    ref: str,
    *,
    payload: dict,
    title: str | None = None,
    summary: str | None = None,
    tenant_id: str = TENANT,
    user_id: str = USER,
    freshness_state: str = "current",
) -> ExecutiveContextContribution:
    return ExecutiveContextContribution(
        contribution_id=ref,
        context_type=context_type,
        title=title or ref,
        summary=summary or ref,
        payload=payload,
        source_provider_id="synthetic_context",
        source_mechanism="synthetic_acceptance_fixture",
        source_record_ref=ref,
        observed_at="2026-07-29T07:55:00Z",
        freshness_state=freshness_state,
        tenant_id=tenant_id,
        user_id=user_id,
        evidence_refs=(_evidence(ref),),
        tags=(context_type,),
    )


def _meeting(
    ref: str,
    start: str,
    end: str,
    *,
    title: str,
    external: int = 0,
    strategic: bool = False,
    preparation_refs: tuple[str, ...] = (),
    all_day: bool = False,
    tenant_id: str = TENANT,
    user_id: str = USER,
) -> ExecutiveContextContribution:
    return _contribution(
        "meeting",
        ref,
        title=title,
        summary=f"{title}; start={start}; end={end}",
        payload={
            "start": start,
            "end": end,
            "title": title,
            "all_day": all_day,
            "status": "confirmed",
            "response_status": "accepted",
            "external_attendee_count": external,
            "strategic": strategic,
            "preparation_refs": list(preparation_refs),
        },
        tenant_id=tenant_id,
        user_id=user_id,
    )


def _commitment(
    ref: str, due: str, *, status: str = "open"
) -> ExecutiveContextContribution:
    return _contribution(
        "commitment",
        ref,
        title=f"Commitment {ref}",
        summary=f"Commitment {ref} due {due}",
        payload={"due_at": due, "status": status, "owner_id": USER},
    )


def _snapshot(
    contributions: tuple[ExecutiveContextContribution, ...],
    *,
    warnings: tuple[str, ...] = (),
    failed_provider_ids: tuple[str, ...] = (),
) -> ExecutiveContextSnapshot:
    return ExecutiveContextSnapshot(
        tenant_id=TENANT,
        user_id=USER,
        request_classification="executive_status",
        contributions=contributions,
        selected_provider_ids=("synthetic_context",),
        successful_provider_ids=("synthetic_context",),
        failed_provider_ids=failed_provider_ids,
        provider_trace={},
        warnings=warnings,
        total_collection_latency_ms=1,
        composed_context="synthetic context",
        context_digest="context_digest",
        snapshot_digest="snapshot_digest",
    )


def _selection(
    snapshot: ExecutiveContextSnapshot, *, budget: int = 20
) -> IntelligenceSelectionRequest:
    return IntelligenceSelectionRequest(
        tenant_id=TENANT,
        user_id=USER,
        request_classification="executive_status",
        ranking_profile="direct_request",
        context_snapshot=snapshot,
        max_signals=budget,
        now=NOW,
    )


def _synthetic_acceptance_snapshot() -> ExecutiveContextSnapshot:
    return _snapshot((
        _meeting(
            "meeting-a",
            "2026-07-29T09:00:00+01:00",
            "2026-07-29T10:00:00+01:00",
            title="Internal planning",
        ),
        _meeting(
            "meeting-b",
            "2026-07-29T10:00:00+01:00",
            "2026-07-29T11:00:00+01:00",
            title="Stakeholder review",
            external=2,
            strategic=True,
        ),
        _meeting(
            "meeting-c",
            "2026-07-29T10:30:00+01:00",
            "2026-07-29T11:30:00+01:00",
            title="Overlap meeting",
        ),
        _commitment("commitment-due", "2026-07-29T17:00:00+01:00"),
        _commitment("commitment-overdue", "2026-07-28T17:00:00+01:00"),
        _contribution(
            "capability_status",
            "provider-calendar",
            title="Calendar provider status",
            summary="Google Calendar is awaiting authorisation; no events were read.",
            payload={
                "provider_id": "google_calendar_context",
                "status": "authorisation_required",
                "required": True,
            },
        ),
    ))


def test_signal_contract_requires_evidence_scope_and_valid_classification() -> None:
    evidence = IntelligenceEvidenceReference.from_context(_evidence("meeting-a"))
    signal = ExecutiveIntelligenceSignal(
        signal_id="sig-1",
        intelligence_type="meeting_count",
        title="Meeting count",
        concise_summary="Three meetings are known from supplied context.",
        structured_payload={"meeting_count": 3},
        source_context_ids=("meeting-a",),
        evidence_references=(evidence,),
        module_id="schedule_summary",
        module_version="1.0.0",
        generated_at=NOW,
        valid_from=NOW,
        stale_after="2026-07-29T23:59:00+01:00",
        freshness_state="current",
        tenant_id=TENANT,
        user_id=USER,
        scope="user",
        severity="low",
        priority="normal",
        confidence=1.0,
        deterministic=True,
        fact_or_inference="derived_fact",
        sensitivity="private",
        tags=("schedule",),
    )

    signal.validate_scope(tenant_id=TENANT, user_id=USER)
    assert "Three meetings" not in json.dumps(signal.safe_trace())

    with pytest.raises(ValueError, match="evidence"):
        ExecutiveIntelligenceSignal(**{
            **signal.__dict__,
            "signal_id": "sig-bad",
            "evidence_references": (),
        })
    with pytest.raises(ValueError, match="severity"):
        ExecutiveIntelligenceSignal(**{
            **signal.__dict__,
            "signal_id": "sig-bad",
            "severity": "huge",
        })
    with pytest.raises(ValueError, match="inference"):
        ExecutiveIntelligenceSignal(**{
            **signal.__dict__,
            "signal_id": "sig-bad",
            "fact_or_inference": "inference",
            "deterministic": True,
        })
    with pytest.raises(ValueError, match="tenant"):
        signal.validate_scope(tenant_id="tenant-2", user_id=USER)


def test_score_contract_rejects_opaque_or_out_of_range_scores() -> None:
    score = IntelligenceScore(
        score_type="meeting_load",
        scale="minutes",
        minimum=0,
        maximum=480,
        value=180,
        meaning="Scheduled meeting minutes in the working day.",
        calculation_version="meeting_load.v1",
        inputs=("meeting-a", "meeting-b"),
        thresholds=(),
        evidence=(IntelligenceEvidenceReference.from_context(_evidence("meeting-a")),),
        confidence=1.0,
        deterministic=True,
    )

    assert score.value == 180
    with pytest.raises(ValueError, match="out of range"):
        IntelligenceScore(**{**score.__dict__, "value": 900})
    with pytest.raises(ValueError, match="meaning"):
        IntelligenceScore(**{**score.__dict__, "meaning": ""})
    with pytest.raises(ValueError, match="evidence"):
        IntelligenceScore(**{**score.__dict__, "evidence": ()})


def test_registry_filters_modules_deterministically_and_rejects_duplicates() -> None:
    registry = IntelligenceRegistry()
    module = ScheduleSummaryModule()
    registry.register(module)

    with pytest.raises(ValueError, match="duplicate"):
        registry.register(module)

    assert registry.lookup("schedule_summary") is module
    assert registry.enabled_modules(deterministic_only=True) == (module,)
    assert registry.by_input_context_type("meeting") == (module,)
    assert registry.by_output_intelligence_type("meeting_count") == (module,)
    registry.set_enabled("schedule_summary", False)
    assert registry.enabled_modules() == ()
    assert registry.health()["schedule_summary"]["enabled"] is False


def test_engine_runs_modules_ranks_signals_and_preserves_evidence() -> None:
    engine = build_default_intelligence_engine()
    snapshot = engine.run(_selection(_synthetic_acceptance_snapshot()))

    types = [signal.intelligence_type for signal in snapshot.signals]
    assert "meeting_count" in types
    assert "scheduled_duration" in types
    assert "meeting_conflict" in types
    assert "longest_focus_block" in types
    assert "back_to_back_meeting_count" in types
    assert "preparation_gap" in types
    assert "commitment_due" in types
    assert "commitment_overdue" in types
    assert "required_context_unavailable" in types
    assert all(signal.evidence_references for signal in snapshot.signals)
    assert all(signal.deterministic for signal in snapshot.signals)
    assert snapshot.safe_trace_metadata()["inference_signal_count"] == 0
    assert (
        "meeting-b"
        in next(
            signal
            for signal in snapshot.signals
            if signal.intelligence_type == "meeting_conflict"
        ).source_context_ids
    )


def test_intelligence_output_is_repeatable_for_same_context() -> None:
    engine = build_default_intelligence_engine()
    request = _selection(_synthetic_acceptance_snapshot())

    first = engine.run(request)
    second = engine.run(request)

    assert first.snapshot_digest == second.snapshot_digest
    assert [signal.safe_trace() for signal in first.signals] == [
        signal.safe_trace() for signal in second.signals
    ]


def test_engine_isolates_failures_rejects_wrong_scope_and_enforces_budget() -> None:
    class BrokenModule:
        definition = IntelligenceModuleDefinition(
            module_id="broken",
            name="Broken",
            version="1.0.0",
            owner="Hermes",
            description="Raises",
            input_context_types=("meeting",),
            optional_context_types=(),
            output_intelligence_types=("broken_signal",),
            deterministic=True,
            required_evidence=True,
            freshness_requirements=("current",),
            minimum_context_requirements=("meeting",),
            tenant_scope="tenant",
            user_scope="user",
            timeout_ms=100,
            execution_priority=1,
            risk_level="low",
            enabled=True,
            lifecycle_state="active",
            calculation_documentation="test",
            test_fixture_refs=("test",),
        )

        def execute(self, request):
            raise RuntimeError("boom")

    registry = IntelligenceRegistry()
    registry.register(BrokenModule())
    registry.register(ScheduleSummaryModule())
    engine = ExecutiveIntelligenceEngine(registry=registry)
    wrong_scope = _snapshot((
        _meeting(
            "meeting-wrong",
            "2026-07-29T09:00:00+01:00",
            "2026-07-29T10:00:00+01:00",
            title="Wrong tenant",
            tenant_id="tenant-2",
        ),
        _meeting(
            "meeting-ok",
            "2026-07-29T11:00:00+01:00",
            "2026-07-29T12:00:00+01:00",
            title="Right tenant",
        ),
    ))

    result = engine.run(_selection(wrong_scope, budget=1))

    assert result.failed_module_ids == ("broken",)
    assert any(
        error.code == IntelligenceErrorCode.MODULE_EXCEPTION for error in result.errors
    )
    assert result.warnings
    assert len(result.signals) == 1
    assert result.safe_trace_metadata()["skipped_signal_count"] >= 1


def test_schedule_modules_handle_empty_conflicts_focus_and_back_to_back() -> None:
    engine = ExecutiveIntelligenceEngine.from_modules((
        ScheduleSummaryModule(),
        ScheduleConflictModule(),
        FocusTimeModule(),
        BackToBackLoadModule(),
    ))
    snapshot = _snapshot((
        _meeting(
            "meeting-a",
            "2026-07-29T09:00:00+01:00",
            "2026-07-29T10:00:00+01:00",
            title="A",
        ),
        _meeting(
            "meeting-b",
            "2026-07-29T10:00:00+01:00",
            "2026-07-29T10:30:00+01:00",
            title="B",
        ),
        _meeting(
            "meeting-c",
            "2026-07-29T11:00:00+01:00",
            "2026-07-29T12:00:00+01:00",
            title="C",
        ),
    ))

    result = engine.run(_selection(snapshot))
    payloads = {
        signal.intelligence_type: signal.structured_payload for signal in result.signals
    }

    assert payloads["meeting_count"]["meeting_count"] == 3
    assert payloads["scheduled_duration"]["scheduled_minutes"] == 150
    assert "meeting_conflict" not in payloads
    assert payloads["longest_focus_block"]["minutes"] == 330
    assert payloads["back_to_back_meeting_count"]["count"] == 1


def test_preparation_commitment_and_availability_modules_are_capability_honest() -> (
    None
):
    engine = ExecutiveIntelligenceEngine.from_modules((
        PreparationGapModule(),
        CommitmentDueModule(),
        ContextAvailabilityModule(),
    ))
    result = engine.run(_selection(_synthetic_acceptance_snapshot()))
    payloads = {
        signal.intelligence_type: signal.structured_payload for signal in result.signals
    }

    assert payloads["preparation_gap"]["meeting_ref"] == "meeting-b"
    assert payloads["commitment_due"]["commitment_ref"] == "commitment-due"
    assert payloads["commitment_overdue"]["commitment_ref"] == "commitment-overdue"
    assert (
        payloads["required_context_unavailable"]["provider_id"]
        == "google_calendar_context"
    )


def test_rendered_intelligence_separates_facts_signals_and_limitations() -> None:
    snapshot = build_default_intelligence_engine().run(
        _selection(_synthetic_acceptance_snapshot())
    )
    rendered = render_intelligence_snapshot_for_reasoning(snapshot, max_chars=2000)

    assert "Executive Intelligence:" in rendered
    assert "Derived executive facts" in rendered
    assert "Attention signals" in rendered
    assert "Data limitations" in rendered
    assert "Inference" not in rendered
    assert "not_executed" in rendered


class RecordingAgent:
    provider = "custom"
    model = "gpt-4.1-mini"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run_conversation(self, message, **kwargs):  # noqa: ANN001
        self.calls.append((message, kwargs))
        return {"final_response": "Intelligence-aware answer."}


def test_orchestrator_receives_intelligence_without_external_calls(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_EXECUTIVE_CONTEXT_PROVIDER_FRAMEWORK_ENABLED", "true")
    monkeypatch.setenv("HERMES_EXECUTIVE_INTELLIGENCE_ENABLED", "true")
    repository = InMemoryExecutiveContextRepository(
        records=(
            ExecutiveContextRecord(
                record_id="ovos.executive_event_journal:meeting-a",
                category="operational",
                source_table="ovos.executive_event_journal",
                source_ref="meeting-a",
                title="Internal planning",
                summary="Internal planning; start=2026-07-29T09:00:00+01:00; end=2026-07-29T10:00:00+01:00",
                metadata={
                    "context_type": "meeting",
                    "start": "2026-07-29T09:00:00+01:00",
                    "end": "2026-07-29T10:00:00+01:00",
                    "title": "Internal planning",
                    "status": "confirmed",
                    "response_status": "accepted",
                },
            ),
            ExecutiveContextRecord(
                record_id="ovos.conversation_signals:commitment-due",
                category="operational",
                source_table="ovos.conversation_signals",
                source_ref="commitment-due",
                title="Commitment due",
                summary="Commitment due today",
                metadata={
                    "context_type": "commitment",
                    "due_at": "2026-07-29T17:00:00+01:00",
                    "status": "open",
                    "owner_id": USER,
                },
            ),
        )
    )
    agent = RecordingAgent()
    sink = InMemoryExecutiveTraceSink()
    turn = ExecutiveTurnInput(
        tenant_id=TENANT,
        conversation_id="conversation-1",
        actor_id=USER,
        actor_name="Nitin",
        platform="local_diagnostic",
        chat_id=None,
        message="What meetings do I have today?",
    )

    result = run_reasoning_with_optional_orchestrator(
        agent=agent,
        message=turn.message,
        conversation_kwargs={"conversation_history": []},
        turn=turn,
        provider="custom",
        model="gpt-4.1-mini",
        enabled=True,
        orchestrator=ExecutiveOrchestrator(
            context_resolver=ExecutiveContextResolver(repository=repository),
            trace_sink=sink,
        ),
    )

    assert result.prepared is not None
    assert "Executive Intelligence:" in agent.calls[0][0]
    assert (
        result.result["executive_orchestrator"]["intelligence_snapshot"]["signal_count"]
        > 0
    )
    completed = next(
        record for record in sink.records if record["stage"] == "reasoning_completed"
    )
    assert completed["executive_intelligence_snapshot"]["signal_count"] > 0
    assert result.result["executive_orchestrator"]["execution_state"] == "not_executed"
