from __future__ import annotations

from dataclasses import replace
import json
import time

import pytest

from gateway.executive_orchestrator import ExecutiveContextLimits, ExecutiveTurnInput
from gateway.executive_context_providers import (
    ContextEvidenceReference,
    CurrentRequestMetadataProvider,
    ExecutiveContextCollectionService,
    ExecutiveContextContribution,
    ExecutiveContextProviderMetadata,
    ExecutiveContextProviderRegistry,
    MCPContextProviderBoundary,
    MockExecutiveContextProvider,
    PersistentProfileProvider,
    RecentConversationProvider,
    classify_mcp_tool_access,
    is_executive_context_mock_provider_enabled,
    is_mcp_context_adapter_enabled,
)


def _turn(message: str = "What can you currently see?") -> ExecutiveTurnInput:
    return ExecutiveTurnInput(
        tenant_id="tenant-1",
        conversation_id="conversation-1",
        actor_id="user-1",
        actor_name="Nitin",
        platform="local_diagnostic",
        chat_id=None,
        message=message,
        session_id="session-1",
        session_key="local:session-1:user-1",
    )


class ProfileAgent:
    _memory_enabled = True
    _user_profile_enabled = True
    _memory_store = object()


def test_contribution_requires_provenance_and_preserves_sensitivity() -> None:
    evidence = ContextEvidenceReference(
        evidence_id="profile:abc123",
        source_provider_id="persistent_profile",
        source_mechanism="internal_memory",
        source_record_ref="profile-digest",
        observed_at="2026-07-29T17:00:00Z",
    )

    contribution = ExecutiveContextContribution(
        contribution_id="ctx-1",
        context_type="identity",
        title="Persistent profile available",
        summary="Profile context is available; raw content is withheld.",
        payload={"available": True},
        source_provider_id="persistent_profile",
        source_mechanism="internal_memory",
        source_record_ref="profile-digest",
        observed_at="2026-07-29T17:00:00Z",
        confidence=0.9,
        freshness_state="current",
        sensitivity="private",
        tenant_id="tenant-1",
        user_id="user-1",
        evidence_refs=(evidence,),
        tags=("profile",),
    )

    assert contribution.sensitivity == "private"
    assert contribution.evidence_refs == (evidence,)
    assert contribution.safe_trace()["source_record_ref"] == "profile-digest"
    assert "raw content" not in json.dumps(contribution.safe_trace()).casefold()


def test_contribution_rejects_missing_provenance_wrong_tenant_and_bad_confidence() -> (
    None
):
    with pytest.raises(ValueError, match="source_provider_id"):
        ExecutiveContextContribution(
            contribution_id="ctx-1",
            context_type="risk",
            title="Risk",
            summary="Risk",
            payload={},
            source_provider_id="",
            source_mechanism="internal",
            source_record_ref="risk-1",
            observed_at="2026-07-29T17:00:00Z",
            tenant_id="tenant-1",
            user_id="user-1",
        )

    valid = ExecutiveContextContribution(
        contribution_id="ctx-1",
        context_type="risk",
        title="Risk",
        summary="Risk",
        payload={},
        source_provider_id="provider",
        source_mechanism="internal",
        source_record_ref="risk-1",
        observed_at="2026-07-29T17:00:00Z",
        tenant_id="tenant-2",
        user_id="user-1",
    )

    with pytest.raises(ValueError, match="tenant"):
        valid.validate_scope(tenant_id="tenant-1", user_id="user-1")

    with pytest.raises(ValueError, match="confidence"):
        replace(valid, confidence=1.5)


def test_provider_registry_rejects_duplicates_and_filters_disabled_providers() -> None:
    registry = ExecutiveContextProviderRegistry()
    provider = CurrentRequestMetadataProvider()
    registry.register(provider)

    with pytest.raises(ValueError, match="duplicate"):
        registry.register(provider)

    assert registry.lookup("current_request_metadata") is provider
    assert registry.providers_for_context_type("capability_status") == (provider,)

    registry.set_enabled("current_request_metadata", False)
    assert registry.providers_for_context_type("capability_status") == ()
    assert registry.health()["current_request_metadata"]["enabled"] is False


def test_collection_selects_internal_providers_deterministically_and_redacts_traces() -> (
    None
):
    registry = ExecutiveContextProviderRegistry()
    registry.register(RecentConversationProvider(max_messages=3))
    registry.register(PersistentProfileProvider())
    registry.register(CurrentRequestMetadataProvider())
    service = ExecutiveContextCollectionService(registry=registry)

    snapshot = service.collect(
        turn=_turn("What can you currently see about my work?"),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(max_context_chars=900),
        conversation_history=[
            {"role": "user", "content": "Private prior task API_KEY=sk-secret"},
            {"role": "assistant", "content": "Private prior answer"},
        ],
        agent=ProfileAgent(),
    )

    assert snapshot.contribution_counts_by_type["message"] == 2
    assert snapshot.contribution_counts_by_type["identity"] == 1
    assert snapshot.contribution_counts_by_type["capability_status"] == 1
    assert snapshot.selected_provider_ids == (
        "current_request_metadata",
        "persistent_profile",
        "recent_conversation",
    )
    assert snapshot.successful_provider_ids == snapshot.selected_provider_ids
    assert "sk-secret" not in json.dumps(snapshot.safe_trace_metadata())
    assert snapshot.context_digest == snapshot.context_digest
    assert snapshot.snapshot_digest.startswith("snapshot_")


def test_collection_isolates_provider_exceptions_and_timeouts() -> None:
    class BrokenProvider:
        metadata = ExecutiveContextProviderMetadata(
            provider_id="broken",
            version="1.0.0",
            provider_type="internal",
            supported_context_types=("risk",),
            source_mechanism="internal_test",
            timeout_ms=1,
        )

        def collect(self, request):
            raise RuntimeError("database unavailable")

    class SlowProvider:
        metadata = ExecutiveContextProviderMetadata(
            provider_id="slow",
            version="1.0.0",
            provider_type="internal",
            supported_context_types=("risk",),
            source_mechanism="internal_test",
            timeout_ms=1,
        )

        def collect(self, request):
            time.sleep(0.003)
            return ()

    registry = ExecutiveContextProviderRegistry()
    registry.register(BrokenProvider())
    registry.register(SlowProvider())
    service = ExecutiveContextCollectionService(registry=registry)

    snapshot = service.collect(
        turn=_turn("What risks should I remember?"),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(),
    )

    assert snapshot.contributions == ()
    assert snapshot.failed_provider_ids == ("broken", "slow")
    assert "provider_failed:broken" in snapshot.warnings
    assert "provider_timeout:slow" in snapshot.warnings


def test_collection_deduplicates_enforces_budget_and_excludes_wrong_scope() -> None:
    class DuplicateProvider:
        metadata = ExecutiveContextProviderMetadata(
            provider_id="duplicate",
            version="1.0.0",
            provider_type="internal",
            supported_context_types=("risk",),
            source_mechanism="internal_test",
        )

        def collect(self, request):
            return (
                ExecutiveContextContribution(
                    contribution_id="risk-1",
                    context_type="risk",
                    title="Risk 1",
                    summary="First risk",
                    payload={},
                    source_provider_id="duplicate",
                    source_mechanism="internal_test",
                    source_record_ref="risk-1",
                    observed_at="2026-07-29T17:00:00Z",
                    tenant_id="tenant-1",
                    user_id="user-1",
                ),
                ExecutiveContextContribution(
                    contribution_id="risk-1",
                    context_type="risk",
                    title="Risk 1 duplicate",
                    summary="Duplicate risk",
                    payload={},
                    source_provider_id="duplicate",
                    source_mechanism="internal_test",
                    source_record_ref="risk-1",
                    observed_at="2026-07-29T17:00:00Z",
                    tenant_id="tenant-1",
                    user_id="user-1",
                ),
                ExecutiveContextContribution(
                    contribution_id="risk-2",
                    context_type="risk",
                    title="Wrong tenant",
                    summary="Must not leak",
                    payload={},
                    source_provider_id="duplicate",
                    source_mechanism="internal_test",
                    source_record_ref="risk-2",
                    observed_at="2026-07-29T17:00:00Z",
                    tenant_id="tenant-2",
                    user_id="user-1",
                ),
            )

    registry = ExecutiveContextProviderRegistry()
    registry.register(DuplicateProvider())
    service = ExecutiveContextCollectionService(registry=registry)

    snapshot = service.collect(
        turn=_turn("What risks should I remember?"),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(max_context_chars=200),
    )

    assert [item.contribution_id for item in snapshot.contributions] == ["risk-1"]
    assert "scope_rejected:duplicate:risk-2" in snapshot.warnings
    assert "duplicate_contribution:duplicate:risk-1" in snapshot.warnings
    assert "Must not leak" not in snapshot.composed_context


def test_mock_provider_defaults_disabled_and_only_runs_when_explicitly_enabled(
    monkeypatch,
) -> None:
    monkeypatch.delenv("HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED", raising=False)
    assert is_executive_context_mock_provider_enabled() is False

    registry = ExecutiveContextProviderRegistry()
    mock = MockExecutiveContextProvider()
    registry.register(mock)
    service = ExecutiveContextCollectionService(registry=registry)

    snapshot = service.collect(
        turn=_turn("What should I focus on?"),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(),
    )

    assert snapshot.selected_provider_ids == ()

    monkeypatch.setenv("HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED", "true")
    enabled_snapshot = service.collect(
        turn=_turn("What should I focus on?"),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(),
    )
    assert enabled_snapshot.contribution_counts_by_type["active_project"] == 1
    assert enabled_snapshot.contribution_counts_by_type["commitment"] == 1
    assert enabled_snapshot.contribution_counts_by_type["priority"] == 1
    assert enabled_snapshot.contribution_counts_by_type["risk"] == 1


def test_mcp_boundary_classifies_write_tools_and_fails_closed_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv("HERMES_MCP_CONTEXT_ADAPTER_ENABLED", raising=False)
    assert is_mcp_context_adapter_enabled() is False

    boundary = MCPContextProviderBoundary()

    assert (
        classify_mcp_tool_access({"name": "gmail.search", "readOnlyHint": True})
        == "read"
    )
    assert classify_mcp_tool_access({"name": "calendar.create_event"}) == "write"
    assert classify_mcp_tool_access({"name": "unknown"}) == "unknown"

    with pytest.raises(RuntimeError, match="disabled"):
        boundary.collect_resource(
            server_id="local-test",
            resource_id="gmail.messages",
            tenant_id="tenant-1",
            user_id="user-1",
        )
