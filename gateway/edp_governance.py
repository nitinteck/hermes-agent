"""EDP Foundation Slice 1 governance repositories and evaluators.

This module is intentionally narrow. It reads bounded governance state from
OVOS/Supabase RPCs and applies immutable code safety ceilings locally. It never
invokes connectors, approvals, or execution adapters.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol
from uuid import UUID


CAPABILITY_STATES = (
    "unavailable",
    "disabled",
    "proposal_only",
    "read_only",
    "approval_required",
    "enabled",
)

_STATE_RANK = {state: index for index, state in enumerate(CAPABILITY_STATES)}

_CODE_SAFETY_CEILINGS: dict[str, tuple[str, str]] = {
    "external_execution": ("unavailable", "live external execution is disabled"),
    "live_execution": ("unavailable", "live external execution is disabled"),
    "send_email": ("unavailable", "email sending is unavailable"),
    "send_message": ("unavailable", "external message sending is unavailable"),
    "create_event": ("unavailable", "calendar/event writes are unavailable"),
    "create_task": ("unavailable", "external task writes are unavailable"),
    "calendar.write": ("unavailable", "calendar writes are unavailable"),
    "gmail.write": ("unavailable", "gmail writes are unavailable"),
    "clickup.write": ("unavailable", "clickup writes are unavailable"),
    "slack.write": ("unavailable", "slack writes are unavailable"),
    "whatsapp.write": ("unavailable", "unauthorised whatsapp sending is unavailable"),
    "crm.write": ("unavailable", "crm writes are unavailable"),
    "self_modification": ("proposal_only", "self-improvement is proposal-only"),
    "improvement_proposals": (
        "proposal_only",
        "proposals may be recorded but not applied",
    ),
}


class GovernanceConfigurationError(RuntimeError):
    """Raised when a governance repository cannot be configured."""


class GovernanceRepositoryError(RuntimeError):
    """Raised when a bounded governance repository call fails."""


@dataclass(frozen=True)
class TenantContext:
    user_id: str | None
    tenant_id: str
    membership_id: str | None = None
    role: str | None = None
    channel: str = "cli"
    actor_type: str = "service"
    request_id: str | None = None
    correlation_id: str | None = None

    @property
    def actor_user_id(self) -> str:
        return self.user_id or "00000000-0000-0000-0000-000000000000"


@dataclass(frozen=True)
class CapabilityTruth:
    capability_key: str
    code_ceiling: str
    database_overlay: str | None
    effective_state: str
    reason: str
    source: str
    conflict: bool = False
    degraded: bool = False
    scope: str | None = None
    expires_at: str | None = None


@dataclass(frozen=True)
class ImprovementProposalInput:
    tenant_id: str
    proposal_type: str
    title: str
    safe_summary: str
    affected_component: str
    proposer_actor_type: str = "system"
    proposer_user_id: str | None = None
    rationale: str | None = None
    proposed_change_ref: str | None = None
    risk_classification: str = "medium"
    correlation_id: str | None = None
    source_event_reference: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class CapabilityTruthRepository(Protocol):
    def resolve(
        self,
        context: TenantContext,
        capability_key: str,
        *,
        environment: str | None = None,
    ) -> Mapping[str, Any]: ...

    def status(
        self, context: TenantContext, *, environment: str | None = None
    ) -> Mapping[str, Any]: ...


class ImprovementProposalRepository(Protocol):
    def create(self, proposal: ImprovementProposalInput) -> Mapping[str, Any]: ...


class TenantContextResolver:
    """Resolve a runtime tenant context from trusted process configuration."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = dict(os.environ if environ is None else environ)

    def resolve(
        self,
        *,
        channel: str = "cli",
        actor_type: str = "service",
        correlation_id: str | None = None,
    ) -> TenantContext:
        tenant_id = self._required_uuid("OVOS_DEFAULT_TENANT_ID")
        user_id = self._optional_uuid("OVOS_DEFAULT_OWNER_USER_ID")
        return TenantContext(
            user_id=user_id,
            tenant_id=tenant_id,
            role=self._environ.get("HERMES_EDP_ACTOR_ROLE", "service"),
            channel=channel,
            actor_type=actor_type,
            correlation_id=correlation_id,
        )

    def _required_uuid(self, name: str) -> str:
        value = self._environ.get(name, "").strip()
        if not value:
            raise GovernanceConfigurationError(f"{name} is required")
        return _validate_uuid(name, value)

    def _optional_uuid(self, name: str) -> str | None:
        value = self._environ.get(name, "").strip()
        return _validate_uuid(name, value) if value else None


class SupabaseGovernanceRepository:
    """Bounded RPC adapter for EDP governance state."""

    def __init__(
        self,
        *,
        supabase_url: str,
        api_key: str,
        bearer_token: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self._api_key = api_key
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        dotenv_path: Path | None = None,
    ) -> SupabaseGovernanceRepository:
        values = _read_env(environ, dotenv_path)
        url = values.get("SUPABASE_URL", "").strip()
        if not url:
            raise GovernanceConfigurationError("SUPABASE_URL is required")
        access_token = values.get("SUPABASE_ACCESS_TOKEN", "").strip()
        anon_key = (
            values.get("SUPABASE_ANON_KEY", "").strip()
            or values.get("SUPABASE_PUBLISHABLE_KEY", "").strip()
        )
        if access_token and anon_key:
            api_key = anon_key
            bearer_token = access_token
        else:
            allow_service_role = (
                values.get("HERMES_EDP_ALLOW_SERVICE_ROLE_RPC", "").strip().lower()
            )
            service_key = (
                values.get("SUPABASE_SECRET_KEY", "").strip()
                or values.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            )
            if allow_service_role not in {"1", "true", "yes"}:
                raise GovernanceConfigurationError(
                    "SUPABASE_ACCESS_TOKEN plus SUPABASE_ANON_KEY is required; "
                    "set HERMES_EDP_ALLOW_SERVICE_ROLE_RPC=true only for bounded operator diagnostics"
                )
            if not service_key:
                raise GovernanceConfigurationError(
                    "SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY is required when service-role RPC is explicitly allowed"
                )
            api_key = service_key
            bearer_token = service_key
        if not api_key or not bearer_token:
            raise GovernanceConfigurationError(
                "Supabase API key and bearer token are required"
            )
        timeout = float(values.get("OVOS_SUPABASE_TIMEOUT_SECONDS", "10") or "10")
        return cls(
            supabase_url=url,
            api_key=api_key,
            bearer_token=bearer_token,
            timeout_seconds=timeout,
        )

    def resolve(
        self,
        context: TenantContext,
        capability_key: str,
        *,
        environment: str | None = None,
    ) -> Mapping[str, Any]:
        return self._rpc(
            "ovos_edp_resolve_effective_capability",
            {
                "p_tenant_id": context.tenant_id,
                "p_actor_user_id": context.actor_user_id,
                "p_capability_key": capability_key,
                "p_channel": context.channel,
                "p_environment": environment,
                "p_correlation_id": context.correlation_id,
            },
        )

    def status(
        self, context: TenantContext, *, environment: str | None = None
    ) -> Mapping[str, Any]:
        return self._rpc(
            "ovos_edp_list_governance_status",
            {
                "p_tenant_id": context.tenant_id,
                "p_actor_user_id": context.actor_user_id,
                "p_channel": context.channel,
                "p_environment": environment,
            },
        )

    def create(self, proposal: ImprovementProposalInput) -> Mapping[str, Any]:
        return self._rpc(
            "ovos_edp_create_improvement_proposal",
            {
                "p_payload": {
                    "tenant_id": proposal.tenant_id,
                    "proposal_type": proposal.proposal_type,
                    "title": proposal.title,
                    "safe_summary": proposal.safe_summary,
                    "rationale": proposal.rationale,
                    "affected_component": proposal.affected_component,
                    "proposed_change_ref": proposal.proposed_change_ref,
                    "risk_classification": proposal.risk_classification,
                    "proposer_actor_type": proposal.proposer_actor_type,
                    "proposer_user_id": proposal.proposer_user_id,
                    "correlation_id": proposal.correlation_id,
                    "source_event_reference": proposal.source_event_reference,
                    "metadata": dict(proposal.metadata),
                }
            },
        )

    def _rpc(self, name: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.supabase_url}/rest/v1/rpc/{name}",
            data=body,
            headers={
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._bearer_token}",
                "Content-Type": "application/json",
                "User-Agent": "hermes-agent-edp-governance/1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:
                raw = response.read()
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise GovernanceRepositoryError(
                f"Governance RPC {name} unavailable"
            ) from exc
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GovernanceRepositoryError(
                f"Governance RPC {name} returned invalid JSON"
            ) from exc
        if not isinstance(parsed, Mapping):
            raise GovernanceRepositoryError(
                f"Governance RPC {name} returned an invalid shape"
            )
        return parsed


class InMemoryGovernanceRepository:
    """Test double for governance repository contracts."""

    def __init__(self) -> None:
        self.capabilities: dict[str, Mapping[str, Any]] = {}
        self.proposals: list[ImprovementProposalInput] = []
        self.available = True

    def resolve(
        self,
        context: TenantContext,
        capability_key: str,
        *,
        environment: str | None = None,
    ) -> Mapping[str, Any]:
        del context, environment
        if not self.available:
            raise GovernanceRepositoryError("unavailable")
        return self.capabilities.get(
            capability_key,
            {
                "capability_key": capability_key,
                "database_overlay_state": None,
                "effective_database_state": "unavailable",
                "reason": "missing test overlay",
                "source": "memory_test_double",
                "conflict": False,
            },
        )

    def status(
        self, context: TenantContext, *, environment: str | None = None
    ) -> Mapping[str, Any]:
        del context, environment
        if not self.available:
            raise GovernanceRepositoryError("unavailable")
        counts: dict[str, int] = {}
        for proposal in self.proposals:
            counts[proposal.proposal_type] = counts.get(proposal.proposal_type, 0) + 1
        return {
            "database_available": True,
            "capability_overlay_count": len(self.capabilities),
            "proposal_counts": counts,
            "approval_enabled": False,
            "execution_enabled": False,
            "connector_enabled": False,
            "source": "memory_test_double",
        }

    def create(self, proposal: ImprovementProposalInput) -> Mapping[str, Any]:
        if not self.available:
            raise GovernanceRepositoryError("unavailable")
        self.proposals.append(proposal)
        return {
            "proposal_id": f"proposal-{len(self.proposals)}",
            "status": "proposed",
            "direct_mutation_performed": False,
            "execution_status": "not_executed",
        }


class CapabilityTruthEvaluator:
    def __init__(self, repository: CapabilityTruthRepository) -> None:
        self.repository = repository

    def evaluate(
        self,
        context: TenantContext,
        capability_key: str,
        *,
        environment: str | None = None,
    ) -> CapabilityTruth:
        key = _safe_capability_key(capability_key)
        code_ceiling, code_reason = _CODE_SAFETY_CEILINGS.get(
            key,
            ("unavailable", "unknown capability key; code default failed closed"),
        )
        try:
            db_result = self.repository.resolve(context, key, environment=environment)
        except GovernanceRepositoryError as exc:
            return CapabilityTruth(
                capability_key=key,
                code_ceiling=code_ceiling,
                database_overlay=None,
                effective_state=_most_restrictive(code_ceiling, "unavailable"),
                reason=f"{code_reason}; governance database unavailable",
                source="code_ceiling+degraded",
                degraded=True,
            )

        db_state = str(db_result.get("effective_database_state") or "unavailable")
        if db_state not in _STATE_RANK:
            db_state = "unavailable"
        effective = _most_restrictive(code_ceiling, db_state)
        reason = str(db_result.get("reason") or code_reason)
        if (
            effective == code_ceiling
            and _STATE_RANK[code_ceiling] < _STATE_RANK[db_state]
        ):
            reason = f"{code_reason}; database overlay cannot relax code ceiling"
        return CapabilityTruth(
            capability_key=key,
            code_ceiling=code_ceiling,
            database_overlay=str(db_result.get("database_overlay_state") or "") or None,
            effective_state=effective,
            reason=reason,
            source=f"code_ceiling+{db_result.get('source') or 'database'}",
            conflict=bool(db_result.get("conflict")),
            degraded=False,
            scope=str(db_result.get("scope") or "") or None,
            expires_at=str(db_result.get("expires_at") or "") or None,
        )


def _most_restrictive(left: str, right: str) -> str:
    if left not in _STATE_RANK or right not in _STATE_RANK:
        return "unavailable"
    return left if _STATE_RANK[left] <= _STATE_RANK[right] else right


def _safe_capability_key(value: str) -> str:
    key = value.strip().lower()
    if not key or len(key) > 128:
        return "unknown"
    if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_.:-" for char in key):
        return "unknown"
    return key


def _validate_uuid(name: str, value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise GovernanceConfigurationError(f"{name} must be a UUID") from exc


def _read_env(
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | None = None,
) -> dict[str, str]:
    values: dict[str, str] = {}
    path = dotenv_path or Path(
        os.environ.get("OVOS_SUPABASE_ENV_FILE", "") or ".env.supabase"
    )
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("'\"")
    values.update({
        key: value
        for key, value in dict(os.environ if environ is None else environ).items()
        if value
    })
    return values
