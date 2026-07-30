from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from urllib.parse import parse_qs, urlparse

import pytest

from gateway.edp_governance import InMemoryGovernanceRepository, TenantContext
from gateway.executive_context_repository import (
    EXECUTIVE_CONTEXT_VERSION,
    ExecutiveContextEvidence,
    ExecutiveContextRecord,
    ExecutiveContextRepositoryError,
    ExecutiveContextResolver,
    InMemoryExecutiveContextRepository,
    SupabaseExecutiveContextRepository,
)
from gateway.executive_orchestrator import ExecutiveContextLimits, ExecutiveTurnInput


TENANT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_ID = "22222222-2222-4222-8222-222222222222"


def _tenant() -> TenantContext:
    return TenantContext(
        user_id=ACTOR_ID,
        tenant_id=TENANT_ID,
        membership_id="membership-1",
        role="owner",
        channel="diagnostic",
        actor_type="human",
        correlation_id="corr-1",
    )


def _turn(message: str = "What can you see about my work?") -> ExecutiveTurnInput:
    return ExecutiveTurnInput(
        tenant_id=TENANT_ID,
        conversation_id="conversation-1",
        actor_id=ACTOR_ID,
        actor_name="Nitin",
        platform="diagnostic",
        chat_id="local",
        message=message,
    )


def _record(
    category: str,
    ref: str,
    summary: str,
    *,
    source_table: str = "ovos.organisation_contexts",
) -> ExecutiveContextRecord:
    return ExecutiveContextRecord(
        record_id=f"{source_table}:{ref}",
        category=category,
        source_table=source_table,
        source_ref=ref,
        title=ref,
        summary=summary,
        evidence_refs=(
            ExecutiveContextEvidence(
                evidence_id=f"{source_table}:id:{ref}",
                source_table=source_table,
                source_ref=ref,
                digest=f"digest-{ref}",
            ),
        ),
    )


def test_in_memory_repository_builds_versioned_immutable_context() -> None:
    repository = InMemoryExecutiveContextRepository(
        records=(
            _record(
                "organisation",
                "om-vidya",
                "Om Vidya Group education programmes are an active work theme.",
            ),
        )
    )

    context = repository.load(
        tenant_context=_tenant(),
        actor_id=ACTOR_ID,
        request_classification="executive_status",
        correlation_id="corr-1",
        limits=ExecutiveContextLimits(),
    )

    assert context.version == EXECUTIVE_CONTEXT_VERSION
    assert context.identity.tenant_id == TENANT_ID
    assert context.source_counts["organisation"] == 1
    assert context.source_counts["governance"] > 0
    assert context.evidence_ids()[0] == "ovos.organisation_contexts:id:om-vidya"
    assert context.context_digest.startswith("context_")
    with pytest.raises(FrozenInstanceError):
        context.correlation_id = "changed"  # type: ignore[misc]


def test_repository_removes_duplicate_records_deterministically() -> None:
    duplicate = _record("knowledge", "fact-1", "Hermes exists.")
    repository = InMemoryExecutiveContextRepository(records=(duplicate, duplicate))

    context = repository.load(
        tenant_context=_tenant(),
        actor_id=ACTOR_ID,
        request_classification="ordinary_conversation",
        correlation_id="corr-2",
        limits=ExecutiveContextLimits(),
    )

    assert [record.record_id for record in context.knowledge] == [duplicate.record_id]


def test_repository_applies_context_limits() -> None:
    repository = InMemoryExecutiveContextRepository(
        records=(
            _record("strategic", "plan-1", "First plan"),
            _record("strategic", "plan-2", "Second plan"),
        )
    )

    context = repository.load(
        tenant_context=_tenant(),
        actor_id=ACTOR_ID,
        request_classification="planning_request",
        correlation_id="corr-3",
        limits=ExecutiveContextLimits(max_decisions=1),
    )

    assert [record.source_ref for record in context.strategic] == ["plan-1"]


def test_resolver_degrades_safely_when_repository_unavailable() -> None:
    resolver = ExecutiveContextResolver(
        repository=InMemoryExecutiveContextRepository(available=False)
    )

    context = resolver.resolve(
        turn=_turn("Hello"),
        request_classification="ordinary_conversation",
        correlation_id="corr-4",
        limits=ExecutiveContextLimits(),
    )

    assert context.degraded is True
    assert "executive_context_repository_unavailable" in context.warnings
    assert context.source_counts["governance"] == 1
    assert "execution remains not_executed" in context.render_for_reasoning(
        max_chars=2000
    )


def test_capability_truth_keeps_execution_unavailable_despite_database_overlay() -> (
    None
):
    governance = InMemoryGovernanceRepository()
    governance.capabilities["send_email"] = {
        "capability_key": "send_email",
        "database_overlay_state": "enabled",
        "effective_database_state": "enabled",
        "reason": "test overlay",
        "source": "memory_test_double",
        "conflict": False,
    }
    repository = InMemoryExecutiveContextRepository(governance_repository=governance)

    context = repository.load(
        tenant_context=_tenant(),
        actor_id=ACTOR_ID,
        request_classification="potentially_executable",
        correlation_id="corr-5",
        limits=ExecutiveContextLimits(),
    )

    email_record = next(
        record for record in context.governance if record.source_ref == "send_email"
    )
    assert "effective_state=unavailable" in email_record.summary
    assert "database_overlay=enabled" in email_record.summary
    proposal_record = next(
        record for record in context.governance if record.source_ref == "status"
    )
    assert "execution_status=not_executed" in proposal_record.summary


def test_safe_trace_and_rendering_do_not_expose_raw_secrets() -> None:
    repository = InMemoryExecutiveContextRepository(
        records=(
            _record(
                "knowledge",
                "secret-fact",
                "Use token=abc123 and key sk-testsecret in the demo.",
                source_table="ovos.knowledge_memories",
            ),
        )
    )

    context = repository.load(
        tenant_context=_tenant(),
        actor_id=ACTOR_ID,
        request_classification="ordinary_conversation",
        correlation_id="corr-6",
        limits=ExecutiveContextLimits(),
    )

    rendered = context.render_for_reasoning(max_chars=5000)
    trace = str(context.to_safe_dict())
    assert "sk-testsecret" not in rendered
    assert "abc123" not in trace
    assert "source_counts" in trace


def test_resolver_records_authenticated_tenant_context_before_loading_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OVOS_DEFAULT_TENANT_ID", TENANT_ID)
    monkeypatch.setenv("OVOS_DEFAULT_OWNER_USER_ID", ACTOR_ID)
    repository = InMemoryExecutiveContextRepository()
    resolver = ExecutiveContextResolver(repository=repository)

    context = resolver.resolve(
        turn=_turn(),
        request_classification="executive_status",
        correlation_id="corr-7",
        limits=ExecutiveContextLimits(),
    )

    assert context.identity.authentication_state == "supabase_auth_configured"
    assert repository.calls == [
        {
            "tenant_id": TENANT_ID,
            "actor_id": ACTOR_ID,
            "request_classification": "executive_status",
        }
    ]


def test_repository_unavailable_exception_is_not_silently_successful() -> None:
    repository = InMemoryExecutiveContextRepository(available=False)

    with pytest.raises(ExecutiveContextRepositoryError):
        repository.load(
            tenant_context=_tenant(),
            actor_id=ACTOR_ID,
            request_classification="ordinary_conversation",
            correlation_id="corr-8",
            limits=ExecutiveContextLimits(),
        )


def test_supabase_repository_uses_ovos_schema_and_tenant_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_requests = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return json.dumps([]).encode("utf-8")

    def _urlopen(request, timeout):  # noqa: ANN001
        del timeout
        captured_requests.append(request)
        return _Response()

    monkeypatch.setattr(
        "gateway.executive_context_repository.urllib.request.urlopen",
        _urlopen,
    )
    repository = SupabaseExecutiveContextRepository(
        supabase_url="https://example.supabase.co",
        api_key="anon-key",
        bearer_token="user-token",
        governance_repository=InMemoryGovernanceRepository(),
    )

    repository.load(
        tenant_context=_tenant(),
        actor_id=ACTOR_ID,
        request_classification="executive_status",
        correlation_id="corr-supabase",
        limits=ExecutiveContextLimits(max_brief_items=1, max_decisions=1),
    )

    assert captured_requests
    first = captured_requests[0]
    assert first.headers["Accept-profile"] == "ovos"
    parsed = urlparse(first.full_url)
    assert parsed.path == "/rest/v1/executive_identities"
    query = parse_qs(parsed.query)
    assert query["tenant_id"] == [f"eq.{TENANT_ID}"]
    assert query["owner_user_id"] == [f"eq.{ACTOR_ID}"]
