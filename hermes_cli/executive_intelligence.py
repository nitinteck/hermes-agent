"""Operator-safe Executive Intelligence diagnostics."""

from __future__ import annotations

import json
from typing import Any

from gateway.executive_context_providers import (
    ContextEvidenceReference,
    ExecutiveContextContribution,
    ExecutiveContextSnapshot,
)
from gateway.executive_intelligence import (
    IntelligenceSelectionRequest,
    are_deterministic_intelligence_modules_enabled,
    are_inference_intelligence_modules_enabled,
    build_default_intelligence_engine,
    build_default_intelligence_registry,
    is_executive_intelligence_enabled,
    is_intelligence_registry_enabled,
)


def intelligence_status() -> dict[str, Any]:
    registry = build_default_intelligence_registry()
    enabled_modules = registry.enabled_modules(deterministic_only=True)
    return {
        "enabled": is_executive_intelligence_enabled(),
        "registry_enabled": is_intelligence_registry_enabled(),
        "deterministic_modules_enabled": (
            are_deterministic_intelligence_modules_enabled()
        ),
        "inference_modules_enabled": are_inference_intelligence_modules_enabled(),
        "external_calls_enabled": False,
        "live_execution_enabled": False,
        "execution_boundary": "not_executed",
        "enabled_module_count": len(enabled_modules),
        "failed_module_count": 0,
        "deterministic_only_mode": True,
        "last_execution_status": "request_scoped",
        "last_snapshot_digest": None,
        "signal_count_by_category": {},
        "safe_error_codes": [],
        "redacted": True,
    }


def intelligence_modules() -> dict[str, Any]:
    registry = build_default_intelligence_registry()
    return {
        "status": "ok",
        "inference_modules_enabled": are_inference_intelligence_modules_enabled(),
        "external_calls_enabled": False,
        "modules": [
            {
                "module_id": module.definition.module_id,
                "name": module.definition.name,
                "version": module.definition.version,
                "deterministic": module.definition.deterministic,
                "enabled": module.definition.enabled,
                "lifecycle_state": module.definition.lifecycle_state,
                "health_state": module.definition.health_state,
                "input_context_types": list(module.definition.input_context_types),
                "output_intelligence_types": list(
                    module.definition.output_intelligence_types
                ),
                "risk_level": module.definition.risk_level,
            }
            for module in registry.enabled_modules(deterministic_only=True)
        ],
        "redacted": True,
    }


def intelligence_diagnostics() -> dict[str, Any]:
    engine = build_default_intelligence_engine()
    snapshot = _synthetic_snapshot()
    result = engine.run(
        IntelligenceSelectionRequest(
            tenant_id="diagnostic-tenant",
            user_id="diagnostic-user",
            request_classification="executive_status",
            ranking_profile="direct_request",
            context_snapshot=snapshot,
            max_signals=8,
            now="2026-07-29T08:00:00+01:00",
        )
    )
    return {
        "status": "ok",
        "external_calls_enabled": False,
        "live_execution_enabled": False,
        "execution_boundary": "not_executed",
        "snapshot": result.safe_trace_metadata(),
        "redacted": True,
    }


def _synthetic_snapshot() -> ExecutiveContextSnapshot:
    evidence = ContextEvidenceReference(
        evidence_id="diagnostic:meeting",
        source_provider_id="synthetic_intelligence_diagnostic",
        source_mechanism="synthetic_operator_diagnostic",
        source_record_ref="diagnostic-meeting",
        observed_at="2026-07-29T07:55:00Z",
        digest="diagnostic",
    )
    meeting = ExecutiveContextContribution(
        contribution_id="diagnostic-meeting",
        context_type="meeting",
        title="Synthetic diagnostic meeting",
        summary="Synthetic diagnostic meeting with no private payload.",
        payload={
            "start": "2026-07-29T09:00:00+01:00",
            "end": "2026-07-29T10:00:00+01:00",
            "status": "confirmed",
            "response_status": "accepted",
        },
        source_provider_id="synthetic_intelligence_diagnostic",
        source_mechanism="synthetic_operator_diagnostic",
        source_record_ref="diagnostic-meeting",
        observed_at="2026-07-29T07:55:00Z",
        tenant_id="diagnostic-tenant",
        user_id="diagnostic-user",
        evidence_refs=(evidence,),
    )
    return ExecutiveContextSnapshot(
        tenant_id="diagnostic-tenant",
        user_id="diagnostic-user",
        request_classification="executive_status",
        contributions=(meeting,),
        selected_provider_ids=("synthetic_intelligence_diagnostic",),
        successful_provider_ids=("synthetic_intelligence_diagnostic",),
        failed_provider_ids=(),
        provider_trace={},
        warnings=(),
        total_collection_latency_ms=0,
        composed_context="synthetic",
        context_digest="synthetic_context",
        snapshot_digest="synthetic_snapshot",
    )


def cmd_status(args: Any) -> None:
    del args
    print(json.dumps(intelligence_status(), sort_keys=True))


def cmd_modules(args: Any) -> None:
    del args
    print(json.dumps(intelligence_modules(), sort_keys=True))


def cmd_diagnostics(args: Any) -> None:
    del args
    print(json.dumps(intelligence_diagnostics(), sort_keys=True))


def register_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "intelligence",
        help="Inspect Executive Intelligence Engine state",
    )
    parser.set_defaults(func=cmd_status)
    subs = parser.add_subparsers(dest="intelligence_command")
    status = subs.add_parser("status", help="Show Executive Intelligence status")
    status.set_defaults(func=cmd_status)
    modules = subs.add_parser("modules", help="List enabled intelligence modules")
    modules.set_defaults(func=cmd_modules)
    diagnostics = subs.add_parser(
        "diagnostics",
        help="Run a synthetic non-external intelligence diagnostic",
    )
    diagnostics.set_defaults(func=cmd_diagnostics)
