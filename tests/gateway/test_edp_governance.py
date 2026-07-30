from __future__ import annotations

import json
from pathlib import Path

import pytest

from gateway.edp_governance import (
    CapabilityTruthEvaluator,
    GovernanceConfigurationError,
    GovernanceRepositoryError,
    ImprovementProposalInput,
    InMemoryGovernanceRepository,
    SupabaseGovernanceRepository,
    TenantContext,
    TenantContextResolver,
)

TENANT_ID = "11111111-1111-4111-8111-111111111111"
USER_ID = "22222222-2222-4222-8222-222222222222"


def test_tenant_context_resolves_only_valid_trusted_identifiers() -> None:
    context = TenantContextResolver({
        "OVOS_DEFAULT_TENANT_ID": TENANT_ID,
        "OVOS_DEFAULT_OWNER_USER_ID": USER_ID,
        "HERMES_EDP_ACTOR_ROLE": "operator",
    }).resolve(channel="diagnostic", actor_type="operator", correlation_id="corr-1")

    assert context.tenant_id == TENANT_ID
    assert context.user_id == USER_ID
    assert context.role == "operator"
    assert context.channel == "diagnostic"
    assert context.actor_type == "operator"
    assert context.correlation_id == "corr-1"


def test_tenant_context_rejects_missing_or_malformed_tenant() -> None:
    with pytest.raises(GovernanceConfigurationError):
        TenantContextResolver({}).resolve()
    with pytest.raises(GovernanceConfigurationError):
        TenantContextResolver({"OVOS_DEFAULT_TENANT_ID": "not-a-uuid"}).resolve()


def test_unknown_capability_fails_closed_without_yaml_fallback() -> None:
    repository = InMemoryGovernanceRepository()
    context = TenantContext(user_id=USER_ID, tenant_id=TENANT_ID)

    truth = CapabilityTruthEvaluator(repository).evaluate(context, "new_live_adapter")

    assert truth.code_ceiling == "unavailable"
    assert truth.effective_state == "unavailable"
    assert truth.source == "code_ceiling+memory_test_double"


def test_database_overlay_cannot_relax_code_prohibited_capability() -> None:
    repository = InMemoryGovernanceRepository()
    repository.capabilities["send_email"] = {
        "capability_key": "send_email",
        "database_overlay_state": "enabled",
        "effective_database_state": "enabled",
        "reason": "operator attempted enablement",
        "source": "database",
        "conflict": False,
    }
    context = TenantContext(user_id=USER_ID, tenant_id=TENANT_ID)

    truth = CapabilityTruthEvaluator(repository).evaluate(context, "send_email")

    assert truth.code_ceiling == "unavailable"
    assert truth.database_overlay == "enabled"
    assert truth.effective_state == "unavailable"
    assert "cannot relax code ceiling" in truth.reason


def test_database_outage_remains_restrictive() -> None:
    repository = InMemoryGovernanceRepository()
    repository.available = False
    context = TenantContext(user_id=USER_ID, tenant_id=TENANT_ID)

    execution = CapabilityTruthEvaluator(repository).evaluate(
        context, "external_execution"
    )
    proposals = CapabilityTruthEvaluator(repository).evaluate(
        context, "improvement_proposals"
    )

    assert execution.degraded is True
    assert execution.effective_state == "unavailable"
    assert proposals.degraded is True
    assert proposals.effective_state == "unavailable"


def test_improvement_proposal_persistence_failure_does_not_directly_mutate() -> None:
    repository = InMemoryGovernanceRepository()
    repository.available = False
    proposal = ImprovementProposalInput(
        tenant_id=TENANT_ID,
        proposal_type="governance",
        title="Review routing rule",
        safe_summary="Create a bounded review proposal only.",
        affected_component="gateway.routing",
    )

    with pytest.raises(GovernanceRepositoryError):
        repository.create(proposal)
    assert repository.proposals == []


def test_improvement_proposal_creation_returns_non_executing_receipt() -> None:
    repository = InMemoryGovernanceRepository()
    proposal = ImprovementProposalInput(
        tenant_id=TENANT_ID,
        proposal_type="governance",
        title="Review capability truth",
        safe_summary="Record an improvement proposal without applying it.",
        affected_component="gateway.edp_governance",
    )

    result = repository.create(proposal)

    assert result["status"] == "proposed"
    assert result["direct_mutation_performed"] is False
    assert result["execution_status"] == "not_executed"
    assert repository.proposals == [proposal]


def test_supabase_repository_requires_user_token_unless_service_role_explicitly_allowed() -> (
    None
):
    with pytest.raises(GovernanceConfigurationError):
        SupabaseGovernanceRepository.from_environment({
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "secret",
        })

    repository = SupabaseGovernanceRepository.from_environment({
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "secret",
        "HERMES_EDP_ALLOW_SERVICE_ROLE_RPC": "true",
    })

    assert repository.supabase_url == "https://example.supabase.co"


def test_supabase_repository_reads_dotenv_without_exposing_secret(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env.supabase"
    env_file.write_text(
        "\n".join([
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_ANON_KEY=anon-key",
            "SUPABASE_ACCESS_TOKEN=user-token",
        ]),
        encoding="utf-8",
    )

    repository = SupabaseGovernanceRepository.from_environment({}, dotenv_path=env_file)

    dumped = json.dumps(repository.__dict__)
    assert "user-token" in dumped
    assert "SUPABASE_ACCESS_TOKEN" not in dumped
