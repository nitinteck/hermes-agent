from __future__ import annotations

import argparse
import json

from gateway.edp_governance import (
    ImprovementProposalInput,
    InMemoryGovernanceRepository,
)
from hermes_cli import governance

TENANT_ID = "11111111-1111-4111-8111-111111111111"
USER_ID = "22222222-2222-4222-8222-222222222222"


class RepositoryFactory:
    def __init__(self, repository: InMemoryGovernanceRepository) -> None:
        self.repository = repository

    def __call__(self, args):  # noqa: ANN001
        del args
        return {"status": "ok", "repository": self.repository}


def _args(**overrides):
    values = {
        "tenant_id": TENANT_ID,
        "user_id": USER_ID,
        "channel": "diagnostic",
        "environment": "test",
        "correlation_id": "corr-1",
        "supabase_env_file": None,
        "capability_keys": None,
        "capability_key": "send_email",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_governance_status_identifies_sources_and_never_enables_execution(
    monkeypatch,
) -> None:
    repository = InMemoryGovernanceRepository()
    repository.capabilities["send_email"] = {
        "capability_key": "send_email",
        "database_overlay_state": "enabled",
        "effective_database_state": "enabled",
        "reason": "test overlay",
        "source": "database",
        "conflict": False,
    }
    monkeypatch.setattr(governance, "_build_repository", RepositoryFactory(repository))

    payload = governance.governance_status(_args(capability_keys=["send_email"]))

    assert payload["status"] == "ok"
    assert payload["database_available"] is True
    assert payload["execution_enabled"] is False
    assert payload["connector_enabled"] is False
    assert payload["external_execution"] == "not_executed"
    assert payload["capabilities"][0]["code_ceiling"] == "unavailable"
    assert payload["capabilities"][0]["database_overlay"] == "enabled"
    assert payload["capabilities"][0]["effective_state"] == "unavailable"
    assert payload["proposal_persistence_status"]["source"] == "memory_test_double"
    assert "TOKEN" not in json.dumps(payload).upper()


def test_capability_truth_status_degrades_fail_closed_without_repository(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        governance,
        "_build_repository",
        lambda _args: {"status": "configuration_error", "reason": "missing db token"},
    )

    payload = governance.capability_truth_status(_args(capability_key="create_task"))

    assert payload["status"] == "degraded"
    assert payload["effective_state"] == "unavailable"
    assert payload["execution_status"] == "not_executed"
    assert payload["external_execution"] == "not_executed"


def test_improvement_proposals_status_returns_bounded_non_executing_shape(
    monkeypatch,
) -> None:
    repository = InMemoryGovernanceRepository()
    repository.create(
        ImprovementProposalInput(
            tenant_id=TENANT_ID,
            proposal_type="governance",
            title="Review capability overlay",
            safe_summary="Digest-only safe summary in database status.",
            affected_component="gateway.edp_governance",
        )
    )
    monkeypatch.setattr(governance, "_build_repository", RepositoryFactory(repository))

    payload = governance.improvement_proposals_status(_args())

    assert payload["status"] == "ok"
    assert payload["proposal_persistence_status"] == "available"
    assert payload["counts"] == {"governance": 1}
    assert payload["direct_mutation_performed"] is False
    assert payload["execution_status"] == "not_executed"


def test_cli_registers_read_only_governance_commands() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    governance.register_cli(subparsers)

    parsed = parser.parse_args([
        "governance",
        "capability-truth",
        "status",
        "gmail.write",
        "--tenant-id",
        TENANT_ID,
        "--user-id",
        USER_ID,
    ])

    assert parsed.command == "governance"
    assert parsed.capability_truth_command == "status"
    assert parsed.capability_key == "gmail.write"
    assert parsed.func is governance.cmd_capability_truth_status
