from __future__ import annotations

from hermes_cli.governance import (
    business_context_diagnostics,
    business_context_status,
    capability_truth_status,
    governance_status,
    improvement_proposals_status,
    ip_guard_status,
    test_packs_list as governance_test_packs_list,
)


def test_governance_status_is_operator_safe_and_non_mutating() -> None:
    status = governance_status()

    assert status["ip_confidentiality_guard_enabled"] is True
    assert status["self_improvement_direct_mutation_enabled"] is False
    assert status["improvement_proposal_application_enabled"] is False
    assert status["approval_engine_enabled"] is False
    assert status["execution_engine_enabled"] is False
    assert status["external_mutations_enabled"] is False
    assert status["live_execution_enabled"] is False
    assert status["mcp_enabled"] is False


def test_ip_guard_and_capability_truth_status_are_redacted() -> None:
    ip_status = ip_guard_status()
    truth_status = capability_truth_status()

    assert ip_status["default_whatsapp_disclosure_class"] == "user_safe"
    assert ip_status["operator_mode_enabled"] is False
    assert truth_status["enabled"] is True
    assert truth_status["external_execution_available"] is False
    assert any(
        item["capability_id"] == "google_calendar"
        and item["authorisation_state"] == "not_authorised"
        for item in truth_status["capabilities"]
    )
    assert "token" not in str(truth_status).casefold()


def test_improvement_and_business_context_statuses_fail_closed() -> None:
    proposals = improvement_proposals_status()
    business = business_context_status()
    diagnostics = business_context_diagnostics()

    assert proposals["direct_mutation_enabled"] is False
    assert proposals["application_status"] == "not_applied"
    assert business["business_knowledge_registry_enabled"] is True
    assert business["publication_requires_owner_review"] is True
    assert business["restricted_context_retrieval_enabled"] is False
    assert diagnostics["restricted_context_available_to_whatsapp"] is False


def test_test_packs_list_names_modular_regression_packs() -> None:
    packs = governance_test_packs_list()["packs"]

    assert "ip_confidentiality" in packs
    assert "capability_honesty" in packs
    assert "planning_safety" in packs
    assert "conversation_continuity" in packs
    assert "business_knowledge" in packs
    assert "executive_usefulness" in packs
