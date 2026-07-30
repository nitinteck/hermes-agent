"""Operator-safe EDP governance diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from gateway.edp_governance import (
    CapabilityTruthEvaluator,
    GovernanceConfigurationError,
    GovernanceRepositoryError,
    SupabaseGovernanceRepository,
    TenantContext,
    TenantContextResolver,
)

DEFAULT_CAPABILITY_KEYS = (
    "external_execution",
    "live_execution",
    "send_email",
    "send_message",
    "create_event",
    "create_task",
    "gmail.write",
    "calendar.write",
    "clickup.write",
    "slack.write",
    "whatsapp.write",
    "crm.write",
    "self_modification",
    "improvement_proposals",
)


def governance_status(args: Any) -> dict[str, Any]:
    environment = getattr(args, "environment", None)
    channel = getattr(args, "channel", "cli")
    context_result = _resolve_context(args, channel=channel)
    if context_result["status"] != "ok":
        return _degraded_status(
            context_result, environment=environment, channel=channel
        )

    context = context_result["context"]
    repository_result = _build_repository(args)
    if repository_result["status"] != "ok":
        return _degraded_status(
            context_result,
            repository_result=repository_result,
            environment=environment,
            channel=channel,
        )

    repository = repository_result["repository"]
    evaluator = CapabilityTruthEvaluator(repository)
    capability_keys = getattr(args, "capability_keys", None) or DEFAULT_CAPABILITY_KEYS
    capabilities = [
        _capability_to_payload(
            evaluator.evaluate(context, key, environment=environment),
        )
        for key in capability_keys
    ]
    try:
        database_status = dict(repository.status(context, environment=environment))
    except GovernanceRepositoryError as exc:
        return _degraded_status(
            context_result,
            repository_result={"status": "unavailable", "reason": str(exc)},
            environment=environment,
            channel=channel,
        )

    return {
        "status": "ok",
        "database_available": bool(database_status.get("database_available")),
        "tenant_context_resolution": "ok",
        "tenant_context": _safe_context(context),
        "environment": environment,
        "channel": channel,
        "capabilities": capabilities,
        "capability_overlay_status": {
            "count": int(database_status.get("capability_overlay_count") or 0),
            "source": database_status.get("source", "database"),
        },
        "proposal_persistence_status": {
            "available": True,
            "counts": database_status.get("proposal_counts") or {},
            "summaries": database_status.get("proposal_summaries") or [],
            "source": database_status.get("source", "database"),
        },
        "audit_write_status": database_status.get("audit_write_status", "unknown"),
        "approval_enabled": False,
        "execution_enabled": False,
        "connector_enabled": False,
        "external_execution": "not_executed",
        "live_execution_enabled": False,
        "redacted": True,
    }


def capability_truth_status(args: Any) -> dict[str, Any]:
    environment = getattr(args, "environment", None)
    channel = getattr(args, "channel", "cli")
    context_result = _resolve_context(args, channel=channel)
    if context_result["status"] != "ok":
        return {
            "status": "degraded",
            "tenant_context_resolution": context_result["status"],
            "reason": context_result["reason"],
            "capability_key": getattr(args, "capability_key", None),
            "effective_state": "unavailable",
            "source": "code_ceiling+degraded",
            "external_execution": "not_executed",
            "redacted": True,
        }
    repository_result = _build_repository(args)
    repository = repository_result.get("repository")
    if repository_result["status"] != "ok" or repository is None:
        from gateway.edp_governance import InMemoryGovernanceRepository

        repository = InMemoryGovernanceRepository()
        repository.available = False
    truth = CapabilityTruthEvaluator(repository).evaluate(
        context_result["context"],
        getattr(args, "capability_key"),
        environment=environment,
    )
    payload = _capability_to_payload(truth)
    payload.update({
        "status": "ok" if not truth.degraded else "degraded",
        "tenant_context": _safe_context(context_result["context"]),
        "environment": environment,
        "channel": channel,
        "external_execution": "not_executed",
        "redacted": True,
    })
    return payload


def improvement_proposals_status(args: Any) -> dict[str, Any]:
    environment = getattr(args, "environment", None)
    channel = getattr(args, "channel", "cli")
    context_result = _resolve_context(args, channel=channel)
    if context_result["status"] != "ok":
        return {
            "status": "degraded",
            "tenant_context_resolution": context_result["status"],
            "reason": context_result["reason"],
            "proposal_persistence_status": "unavailable",
            "counts": {},
            "summaries": [],
            "external_execution": "not_executed",
            "redacted": True,
        }
    repository_result = _build_repository(args)
    if repository_result["status"] != "ok":
        return {
            "status": "degraded",
            "tenant_context_resolution": "ok",
            "repository_status": repository_result["status"],
            "reason": repository_result["reason"],
            "proposal_persistence_status": "unavailable",
            "counts": {},
            "summaries": [],
            "external_execution": "not_executed",
            "redacted": True,
        }
    try:
        database_status = dict(
            repository_result["repository"].status(
                context_result["context"], environment=environment
            )
        )
    except GovernanceRepositoryError as exc:
        return {
            "status": "degraded",
            "tenant_context_resolution": "ok",
            "repository_status": "unavailable",
            "reason": str(exc),
            "proposal_persistence_status": "unavailable",
            "counts": {},
            "summaries": [],
            "external_execution": "not_executed",
            "redacted": True,
        }
    return {
        "status": "ok",
        "tenant_context": _safe_context(context_result["context"]),
        "environment": environment,
        "channel": channel,
        "proposal_persistence_status": "available",
        "counts": database_status.get("proposal_counts") or {},
        "summaries": database_status.get("proposal_summaries") or [],
        "source": database_status.get("source", "database"),
        "direct_mutation_performed": False,
        "execution_status": "not_executed",
        "external_execution": "not_executed",
        "redacted": True,
    }


def cmd_status(args: Any) -> int:
    _print_payload(governance_status(args))
    return 0


def cmd_capability_truth_status(args: Any) -> int:
    _print_payload(capability_truth_status(args))
    return 0


def cmd_improvement_proposals_status(args: Any) -> int:
    _print_payload(improvement_proposals_status(args))
    return 0


def register_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "governance",
        help="Inspect EDP governance state without enabling execution",
    )
    parser.set_defaults(func=cmd_status)
    _add_common_flags(parser)
    subs = parser.add_subparsers(dest="governance_command")

    status = subs.add_parser("status", help="Show EDP governance status")
    _add_common_flags(status)
    status.add_argument(
        "--capability-key",
        dest="capability_keys",
        action="append",
        help="Capability key to include; may be repeated",
    )
    status.set_defaults(func=cmd_status)

    capability = subs.add_parser("capability-truth", help="Inspect Capability Truth")
    capability_subs = capability.add_subparsers(dest="capability_truth_command")
    capability_status = capability_subs.add_parser(
        "status",
        help="Show effective non-executing capability state",
    )
    _add_common_flags(capability_status)
    capability_status.add_argument("capability_key", help="Capability key to inspect")
    capability_status.set_defaults(func=cmd_capability_truth_status)

    proposals = subs.add_parser(
        "improvement-proposals",
        help="Inspect durable Improvement Proposal status",
    )
    proposal_subs = proposals.add_subparsers(dest="improvement_proposals_command")
    proposal_status = proposal_subs.add_parser(
        "status",
        help="Show counts and bounded safe summaries by status",
    )
    _add_common_flags(proposal_status)
    proposal_status.set_defaults(func=cmd_improvement_proposals_status)


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--tenant-id", help="Trusted tenant UUID override for diagnostics"
    )
    parser.add_argument(
        "--user-id", help="Trusted actor user UUID override for diagnostics"
    )
    parser.add_argument("--channel", default="cli", help="Runtime channel scope")
    parser.add_argument("--environment", help="Runtime environment scope")
    parser.add_argument("--correlation-id", help="Safe correlation id for audit traces")
    parser.add_argument(
        "--supabase-env-file",
        type=Path,
        help="Path to Supabase environment file; values are never printed",
    )


def _resolve_context(args: Any, *, channel: str) -> dict[str, Any]:
    environ: dict[str, str] | None = None
    if getattr(args, "tenant_id", None) or getattr(args, "user_id", None):
        environ = dict()
        if getattr(args, "tenant_id", None):
            environ["OVOS_DEFAULT_TENANT_ID"] = args.tenant_id
        if getattr(args, "user_id", None):
            environ["OVOS_DEFAULT_OWNER_USER_ID"] = args.user_id
    try:
        context = TenantContextResolver(environ).resolve(
            channel=channel,
            actor_type="operator",
            correlation_id=getattr(args, "correlation_id", None),
        )
    except GovernanceConfigurationError as exc:
        return {"status": "configuration_error", "reason": str(exc)}
    return {"status": "ok", "context": context}


def _build_repository(args: Any) -> dict[str, Any]:
    try:
        repository = SupabaseGovernanceRepository.from_environment(
            dotenv_path=getattr(args, "supabase_env_file", None),
        )
    except (GovernanceConfigurationError, ValueError) as exc:
        return {"status": "configuration_error", "reason": str(exc)}
    return {"status": "ok", "repository": repository}


def _degraded_status(
    context_result: Mapping[str, Any],
    *,
    repository_result: Mapping[str, Any] | None = None,
    environment: str | None,
    channel: str,
) -> dict[str, Any]:
    reason = str(
        (repository_result or context_result).get("reason", "governance unavailable")
    )
    return {
        "status": "degraded",
        "database_available": False,
        "tenant_context_resolution": context_result["status"],
        "environment": environment,
        "channel": channel,
        "reason": reason,
        "capabilities": [
            {
                "capability_key": key,
                "code_ceiling": "unavailable"
                if key != "improvement_proposals"
                else "proposal_only",
                "database_overlay": None,
                "effective_state": "unavailable",
                "source": "code_ceiling+degraded",
                "degraded": True,
            }
            for key in DEFAULT_CAPABILITY_KEYS
        ],
        "capability_overlay_status": {"count": 0, "source": "unavailable"},
        "proposal_persistence_status": {
            "available": False,
            "counts": {},
            "summaries": [],
            "source": "unavailable",
        },
        "audit_write_status": "unavailable",
        "approval_enabled": False,
        "execution_enabled": False,
        "connector_enabled": False,
        "external_execution": "not_executed",
        "live_execution_enabled": False,
        "redacted": True,
    }


def _capability_to_payload(truth: Any) -> dict[str, Any]:
    return {
        "capability_key": truth.capability_key,
        "code_ceiling": truth.code_ceiling,
        "database_overlay": truth.database_overlay,
        "effective_state": truth.effective_state,
        "reason": truth.reason,
        "scope": truth.scope,
        "expiry": truth.expires_at,
        "source": truth.source,
        "conflict": truth.conflict,
        "degraded": truth.degraded,
        "execution_status": "not_executed",
    }


def _safe_context(context: TenantContext) -> dict[str, Any]:
    return {
        "tenant_id": context.tenant_id,
        "actor_user_id_present": context.user_id is not None,
        "membership_id_present": context.membership_id is not None,
        "role": context.role,
        "channel": context.channel,
        "actor_type": context.actor_type,
        "correlation_id": context.correlation_id,
    }


def _print_payload(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))
