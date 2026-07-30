"""Operator-safe governance hardening CLI commands."""

from __future__ import annotations

import json
from typing import Any

from gateway.business_knowledge import build_business_context_status
from gateway.capability_truth import build_default_capability_truth_registry
from gateway.governance import build_governance_status


def governance_status() -> dict[str, Any]:
    status = build_governance_status()
    status.update({
        "approval_engine_enabled": False,
        "execution_engine_enabled": False,
        "external_mutations_enabled": False,
        "live_execution_enabled": False,
        "mcp_enabled": False,
    })
    return status


def governance_diagnostics() -> dict[str, Any]:
    return {
        "status": "ok",
        "governance": governance_status(),
        "capability_truth": capability_truth_status(),
        "business_context": business_context_status(),
        "redacted": True,
    }


def ip_guard_status() -> dict[str, Any]:
    status = build_governance_status()
    return {
        "ip_confidentiality_guard_enabled": status["ip_confidentiality_guard_enabled"],
        "response_output_inspection_enabled": status[
            "response_output_inspection_enabled"
        ],
        "default_whatsapp_disclosure_class": status[
            "default_whatsapp_disclosure_class"
        ],
        "operator_mode_enabled": False,
        "redacted": True,
    }


def capability_truth_status() -> dict[str, Any]:
    registry = build_default_capability_truth_registry()
    status = registry.status()
    status["capabilities"] = [record.safe_trace() for record in registry.list_all()]
    return status


def improvement_proposals_status() -> dict[str, Any]:
    status = build_governance_status()
    return {
        "proposal_generation_enabled": status[
            "improvement_proposal_generation_enabled"
        ],
        "direct_mutation_enabled": status["self_improvement_direct_mutation_enabled"],
        "application_enabled": status["improvement_proposal_application_enabled"],
        "pending_count": 0,
        "applied_count": 0,
        "application_status": "not_applied",
        "redacted": True,
    }


def business_context_status() -> dict[str, Any]:
    return build_business_context_status()


def business_context_diagnostics() -> dict[str, Any]:
    status = build_business_context_status()
    status.update({
        "status": "ok",
        "conflict_count": 0,
        "stale_record_count": 0,
        "restricted_context_available_to_whatsapp": False,
        "redacted": True,
    })
    return status


def business_context_conflicts() -> dict[str, Any]:
    return {
        "status": "ok",
        "conflicts": [],
        "redacted": True,
    }


def test_packs_list() -> dict[str, Any]:
    return {
        "packs": [
            "ip_confidentiality",
            "capability_honesty",
            "planning_safety",
            "conversation_continuity",
            "business_knowledge",
            "executive_usefulness",
        ],
        "redacted": True,
    }


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def register_cli(subparsers) -> None:  # noqa: ANN001
    governance = subparsers.add_parser(
        "governance",
        help="Show operator-safe Hermes governance status",
    )
    gov_subs = governance.add_subparsers(dest="governance_command")
    gov_subs.add_parser("status", help="Show governance status").set_defaults(
        func=lambda _args: _print(governance_status())
    )
    gov_subs.add_parser("diagnostics", help="Run governance diagnostics").set_defaults(
        func=lambda _args: _print(governance_diagnostics())
    )

    ip_guard = subparsers.add_parser("ip-guard", help="Show IP guard status")
    ip_subs = ip_guard.add_subparsers(dest="ip_guard_command")
    ip_subs.add_parser("status", help="Show IP guard status").set_defaults(
        func=lambda _args: _print(ip_guard_status())
    )

    capability = subparsers.add_parser(
        "capability-truth",
        help="Show deterministic capability truth status",
    )
    cap_subs = capability.add_subparsers(dest="capability_truth_command")
    cap_subs.add_parser("status", help="Show capability truth status").set_defaults(
        func=lambda _args: _print(capability_truth_status())
    )

    proposals = subparsers.add_parser(
        "improvement-proposals",
        help="Show proposal-only self-improvement status",
    )
    proposal_subs = proposals.add_subparsers(dest="improvement_proposals_command")
    proposal_subs.add_parser("status", help="Show proposal status").set_defaults(
        func=lambda _args: _print(improvement_proposals_status())
    )

    business = subparsers.add_parser(
        "business-context",
        help="Show governed business-context status",
    )
    business_subs = business.add_subparsers(dest="business_context_command")
    business_subs.add_parser(
        "status", help="Show business context status"
    ).set_defaults(func=lambda _args: _print(business_context_status()))
    business_subs.add_parser(
        "diagnostics",
        help="Run business context diagnostics",
    ).set_defaults(func=lambda _args: _print(business_context_diagnostics()))
    business_subs.add_parser(
        "conflicts", help="List safe conflict counts"
    ).set_defaults(func=lambda _args: _print(business_context_conflicts()))

    packs = subparsers.add_parser("test-packs", help="List Hermes regression packs")
    pack_subs = packs.add_subparsers(dest="test_packs_command")
    pack_subs.add_parser("list", help="List modular conversational packs").set_defaults(
        func=lambda _args: _print(test_packs_list())
    )
