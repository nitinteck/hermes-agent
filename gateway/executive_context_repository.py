"""Executive Context Repository for Hermes reasoning turns.

This module is the Slice 2 boundary for executive context assembly. It resolves
tenant-scoped context into immutable data objects before intelligence,
reasoning, or planning run. It does not invoke connectors, adapters, tools,
subprocesses, local YAML, or external execution interfaces.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Protocol
from uuid import UUID

from gateway.edp_governance import (
    CapabilityTruthEvaluator,
    GovernanceConfigurationError,
    GovernanceRepositoryError,
    InMemoryGovernanceRepository,
    SupabaseGovernanceRepository,
    TenantContext,
    TenantContextResolver,
)

EXECUTIVE_CONTEXT_VERSION = "hermes.executive_context.v1"

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


class ExecutiveContextRepositoryError(RuntimeError):
    """Raised when the authoritative Executive Context repository cannot load."""


@dataclass(frozen=True)
class ExecutiveContextIdentity:
    tenant_id: str
    actor_id: str
    actor_user_id: str | None
    membership_id: str | None
    role: str | None
    channel: str
    actor_type: str
    authentication_state: str

    def safe_trace(self) -> dict[str, Any]:
        return {
            "tenant_id_digest": _digest(self.tenant_id)[:16],
            "actor_id_digest": _digest(self.actor_id)[:16],
            "actor_user_id_present": self.actor_user_id is not None,
            "membership_id_present": self.membership_id is not None,
            "role": _safe_label(self.role),
            "channel": _safe_label(self.channel),
            "actor_type": _safe_label(self.actor_type),
            "authentication_state": _safe_label(self.authentication_state),
        }


@dataclass(frozen=True)
class ExecutiveContextEvidence:
    evidence_id: str
    source_table: str
    source_ref: str
    digest: str | None = None
    sensitivity: str = "internal"

    def safe_trace(self) -> dict[str, str | None]:
        return {
            "evidence_id": _safe_label(self.evidence_id),
            "source_table": _safe_label(self.source_table),
            "source_ref": _safe_label(self.source_ref),
            "digest": _safe_label(self.digest) if self.digest else None,
            "sensitivity": _safe_label(self.sensitivity),
        }


@dataclass(frozen=True)
class ExecutiveContextRecord:
    record_id: str
    category: str
    source_table: str
    source_ref: str
    title: str
    summary: str
    confidence: float = 1.0
    sensitivity: str = "internal"
    observed_at: str | None = None
    evidence_refs: tuple[ExecutiveContextEvidence, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.record_id or not self.category or not self.source_table:
            raise ValueError("context record requires id, category and source_table")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("context confidence must be between 0 and 1")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "record_id": _safe_label(self.record_id),
            "category": _safe_label(self.category),
            "source_table": _safe_label(self.source_table),
            "source_ref": _safe_label(self.source_ref),
            "confidence": round(float(self.confidence), 3),
            "sensitivity": _safe_label(self.sensitivity),
            "observed_at": _safe_label(self.observed_at),
            "evidence_ids": [item.evidence_id for item in self.evidence_refs],
        }


@dataclass(frozen=True)
class ExecutiveContext:
    version: str
    correlation_id: str
    request_classification: str
    identity: ExecutiveContextIdentity
    organisation: tuple[ExecutiveContextRecord, ...] = ()
    strategic: tuple[ExecutiveContextRecord, ...] = ()
    operational: tuple[ExecutiveContextRecord, ...] = ()
    governance: tuple[ExecutiveContextRecord, ...] = ()
    knowledge: tuple[ExecutiveContextRecord, ...] = ()
    evidence_refs: tuple[ExecutiveContextEvidence, ...] = ()
    warnings: tuple[str, ...] = ()
    degraded: bool = False
    generated_at: str = field(default_factory=lambda: _now_iso())

    @property
    def records(self) -> tuple[ExecutiveContextRecord, ...]:
        return (
            *self.organisation,
            *self.strategic,
            *self.operational,
            *self.governance,
            *self.knowledge,
        )

    @property
    def source_counts(self) -> Mapping[str, int]:
        counts: dict[str, int] = {"identity": 1}
        for record in self.records:
            counts[record.category] = counts.get(record.category, 0) + 1
        return counts

    @property
    def context_digest(self) -> str:
        return (
            f"context_{_digest(json.dumps(self.to_safe_dict(), sort_keys=True))[:16]}"
        )

    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.evidence_id for item in self.evidence_refs))

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "correlation_id": _safe_label(self.correlation_id),
            "request_classification": _safe_label(self.request_classification),
            "identity": self.identity.safe_trace(),
            "source_counts": dict(self.source_counts),
            "records": [record.safe_trace() for record in self.records],
            "evidence_refs": [item.safe_trace() for item in self.evidence_refs],
            "warnings": [_safe_label(item) for item in self.warnings],
            "degraded": self.degraded,
            "generated_at": self.generated_at,
        }

    def render_for_reasoning(self, *, max_chars: int) -> str:
        lines = [
            "Authoritative Executive Context:",
            f"- version: {self.version}",
            f"- correlation_id: {_safe_label(self.correlation_id)}",
            f"- request_classification: {_safe_label(self.request_classification)}",
            f"- tenant_digest: {_digest(self.identity.tenant_id)[:16]}",
            f"- actor_digest: {_digest(self.identity.actor_id)[:16]}",
            f"- authentication_state: {_safe_label(self.identity.authentication_state)}",
            f"- execution_boundary: not_executed",
        ]
        if self.degraded:
            lines.append("- repository_state: degraded")
        for warning in self.warnings:
            lines.append(f"- warning: {_safe_label(warning)}")
        for section_name, records in (
            ("organisation", self.organisation),
            ("strategic", self.strategic),
            ("operational", self.operational),
            ("governance", self.governance),
            ("knowledge", self.knowledge),
        ):
            if not records:
                continue
            lines.append(f"{section_name}:")
            for record in records:
                lines.append(
                    f"- [{_safe_label(record.source_table)}:{_safe_label(record.source_ref)}] "
                    f"{_safe_label(record.title)}: {_redact_secrets(record.summary)} "
                    f"(confidence={round(float(record.confidence), 2)} sensitivity={_safe_label(record.sensitivity)})"
                )
        rendered = "\n".join(lines)
        if len(rendered) <= max_chars:
            return rendered
        return rendered[: max(0, max_chars - 30)].rstrip() + "\n[context truncated]"

    def to_context_items(self) -> Mapping[str, tuple[Any, ...]]:
        from gateway.executive_orchestrator import ContextItem

        grouped: dict[str, list[ContextItem]] = {}
        for record in self.records:
            grouped.setdefault(record.category, []).append(
                ContextItem(
                    source=record.category,
                    reference_id=f"{record.source_table}:{record.source_ref}",
                    title=record.title,
                    summary=record.summary,
                )
            )
        return {key: tuple(value) for key, value in grouped.items()}

    def to_provider_snapshot(self) -> Any:
        from gateway.executive_context_providers import (
            ContextEvidenceReference,
            ExecutiveContextContribution,
            ExecutiveContextSnapshot,
        )

        contributions: list[ExecutiveContextContribution] = []
        for record in self.records:
            context_type = str(record.metadata.get("context_type") or record.category)
            contributions.append(
                ExecutiveContextContribution(
                    contribution_id=record.record_id,
                    context_type=context_type,
                    title=record.title,
                    summary=record.summary,
                    payload={
                        "trace_category": record.category,
                        "context_type": context_type,
                        "source_table": record.source_table,
                        **{
                            str(key): value
                            for key, value in record.metadata.items()
                            if isinstance(key, str)
                        },
                    },
                    source_provider_id="executive_context_repository",
                    source_mechanism="edp_repository",
                    source_record_ref=f"{record.source_table}:{record.source_ref}",
                    observed_at=record.observed_at or self.generated_at,
                    confidence=record.confidence,
                    sensitivity=record.sensitivity,
                    tenant_id=self.identity.tenant_id,
                    user_id=self.identity.actor_id,
                    evidence_refs=tuple(
                        ContextEvidenceReference(
                            evidence_id=item.evidence_id,
                            source_provider_id="executive_context_repository",
                            source_mechanism="edp_repository",
                            source_record_ref=item.source_ref,
                            observed_at=record.observed_at or self.generated_at,
                            digest=item.digest,
                        )
                        for item in record.evidence_refs
                    ),
                    tags=(record.category, context_type, record.source_table),
                )
            )
        return ExecutiveContextSnapshot(
            tenant_id=self.identity.tenant_id,
            user_id=self.identity.actor_id,
            request_classification=self.request_classification,
            contributions=tuple(contributions),
            selected_provider_ids=("executive_context_repository",),
            successful_provider_ids=("executive_context_repository",)
            if not self.degraded
            else (),
            failed_provider_ids=()
            if not self.degraded
            else ("executive_context_repository",),
            provider_trace={
                "executive_context_repository": {
                    "status": "degraded" if self.degraded else "ok",
                    "accepted_contributions": len(contributions),
                    "source_counts": dict(self.source_counts),
                }
            },
            warnings=self.warnings,
            total_collection_latency_ms=0,
            composed_context=self.render_for_reasoning(max_chars=6_000),
            context_digest=self.context_digest,
            snapshot_digest=f"snapshot_{_digest(self.context_digest)[:16]}",
        )


class ExecutiveContextRepository(Protocol):
    def load(
        self,
        *,
        tenant_context: TenantContext,
        actor_id: str,
        request_classification: str,
        correlation_id: str,
        limits: Any,
        environment: str | None = None,
    ) -> ExecutiveContext: ...


class InMemoryExecutiveContextRepository:
    """Focused test double for the Executive Context Repository contract."""

    def __init__(
        self,
        *,
        records: tuple[ExecutiveContextRecord, ...] = (),
        governance_repository: Any | None = None,
        available: bool = True,
    ) -> None:
        self.records = records
        self.available = available
        self.governance_repository = (
            governance_repository or InMemoryGovernanceRepository()
        )
        self.calls: list[dict[str, Any]] = []

    def load(
        self,
        *,
        tenant_context: TenantContext,
        actor_id: str,
        request_classification: str,
        correlation_id: str,
        limits: Any,
        environment: str | None = None,
    ) -> ExecutiveContext:
        self.calls.append({
            "tenant_id": tenant_context.tenant_id,
            "actor_id": actor_id,
            "request_classification": request_classification,
        })
        if not self.available:
            raise ExecutiveContextRepositoryError("repository unavailable")
        return _build_context_from_records(
            tenant_context=tenant_context,
            actor_id=actor_id,
            request_classification=request_classification,
            correlation_id=correlation_id,
            records=(
                *self.records,
                *self._governance_records(tenant_context, environment),
            ),
            limits=limits,
            warnings=(),
            degraded=False,
        )

    def _governance_records(
        self, tenant_context: TenantContext, environment: str | None
    ) -> tuple[ExecutiveContextRecord, ...]:
        evaluator = CapabilityTruthEvaluator(self.governance_repository)
        records: list[ExecutiveContextRecord] = []
        for key in DEFAULT_CAPABILITY_KEYS:
            truth = evaluator.evaluate(tenant_context, key, environment=environment)
            records.append(_capability_record(truth))
        try:
            status = self.governance_repository.status(
                tenant_context, environment=environment
            )
        except GovernanceRepositoryError:
            status = {"proposal_counts": {}, "proposal_summaries": []}
        records.append(_proposal_status_record(status))
        return tuple(records)


class SupabaseExecutiveContextRepository:
    """Supabase/OVOS-backed Executive Context Repository."""

    def __init__(
        self,
        *,
        supabase_url: str,
        api_key: str,
        bearer_token: str,
        governance_repository: Any,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self._api_key = api_key
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds
        self.governance_repository = governance_repository
        self._request_cache: dict[str, tuple[Mapping[str, Any], ...]] = {}
        self._load_warnings: list[str] = []

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
        dotenv_path: Path | None = None,
    ) -> SupabaseExecutiveContextRepository:
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
                    "service-role diagnostics require HERMES_EDP_ALLOW_SERVICE_ROLE_RPC=true"
                )
            if not service_key:
                raise GovernanceConfigurationError("service-role key is required")
            api_key = service_key
            bearer_token = service_key
        governance_repository = SupabaseGovernanceRepository.from_environment(
            values, dotenv_path=dotenv_path
        )
        timeout = float(values.get("OVOS_SUPABASE_TIMEOUT_SECONDS", "10") or "10")
        return cls(
            supabase_url=url,
            api_key=api_key,
            bearer_token=bearer_token,
            governance_repository=governance_repository,
            timeout_seconds=timeout,
        )

    def load(
        self,
        *,
        tenant_context: TenantContext,
        actor_id: str,
        request_classification: str,
        correlation_id: str,
        limits: Any,
        environment: str | None = None,
    ) -> ExecutiveContext:
        self._request_cache = {}
        self._load_warnings = []
        records: list[ExecutiveContextRecord] = []
        warnings: list[str] = []
        try:
            records.extend(self._load_identity_records(tenant_context, limits))
            records.extend(self._load_organisation_records(tenant_context, limits))
            records.extend(self._load_strategic_records(tenant_context, limits))
            records.extend(self._load_operational_records(tenant_context, limits))
            records.extend(self._load_knowledge_records(tenant_context, limits))
        except ExecutiveContextRepositoryError:
            raise
        except Exception as exc:
            raise ExecutiveContextRepositoryError("EDP context query failed") from exc
        warnings.extend(self._load_warnings)
        try:
            records.extend(self._load_governance_records(tenant_context, environment))
        except Exception:
            warnings.append("governance_context_degraded")
        return _build_context_from_records(
            tenant_context=tenant_context,
            actor_id=actor_id,
            request_classification=request_classification,
            correlation_id=correlation_id,
            records=tuple(records),
            limits=limits,
            warnings=tuple(warnings),
            degraded=False,
        )

    def _load_identity_records(
        self, tenant_context: TenantContext, limits: Any
    ) -> list[ExecutiveContextRecord]:
        rows = self._rpc_rows(
            "ovos_list_executive_identities",
            {
                "p_tenant_id": tenant_context.tenant_id,
                "p_owner_user_id": tenant_context.actor_user_id,
                "p_active_only": True,
            },
        )[: min(2, _limit(limits, "max_brief_items", 5))]
        return [
            _record(
                category="identity",
                source_table="ovos.executive_identities",
                source_ref=str(row.get("id") or ""),
                title=str(
                    row.get("preferred_name")
                    or row.get("full_name")
                    or "Executive identity"
                ),
                summary="; ".join(
                    part
                    for part in (
                        f"name={row.get('preferred_name') or row.get('full_name')}",
                        f"title={row.get('primary_title')}",
                        f"organisation={row.get('primary_organisation')}",
                    )
                    if part and not part.endswith("=None")
                ),
                confidence=_confidence(row),
                sensitivity=str(row.get("visibility") or "private"),
                observed_at=str(row.get("updated_at") or row.get("created_at") or ""),
                evidence_refs=_evidence(row, "ovos.executive_identities"),
            )
            for row in rows
        ]

    def _load_organisation_records(
        self, tenant_context: TenantContext, limits: Any
    ) -> list[ExecutiveContextRecord]:
        records: list[ExecutiveContextRecord] = []
        for row in self._rpc_rows(
            "ovos_search_organisation_contexts",
            {
                "p_tenant_id": tenant_context.tenant_id,
                "p_owner_user_id": tenant_context.actor_user_id,
                "p_query": None,
                "p_active_only": True,
            },
        )[: _limit(limits, "max_brief_items", 5)]:
            records.append(
                _record(
                    category="organisation",
                    source_table="ovos.organisation_contexts",
                    source_ref=str(row.get("id") or ""),
                    title=str(row.get("canonical_name") or "Organisation"),
                    summary=_join_summary(
                        mission=row.get("mission"),
                        brands=_json_list(row.get("brands")),
                        programmes=_json_list(row.get("programme_names")),
                        initiatives=_json_list(row.get("active_initiatives")),
                    ),
                    confidence=_confidence(row),
                    sensitivity=str(row.get("visibility") or "private"),
                    observed_at=str(
                        row.get("updated_at") or row.get("created_at") or ""
                    ),
                    evidence_refs=_evidence(row, "ovos.organisation_contexts"),
                )
            )
        for table, title_field, max_attr in (
            ("team_members", "canonical_name", "max_decisions"),
            ("responsibility_assignments", "subject", "max_decisions"),
        ):
            rpc_name = (
                "ovos_search_team_members"
                if table == "team_members"
                else "ovos_search_responsibility_assignments"
            )
            query_key = (
                "p_query" if table == "team_members" else "p_subject_text"
            )
            rows = self._rpc_rows(
                rpc_name,
                {
                    "p_tenant_id": tenant_context.tenant_id,
                    "p_owner_user_id": tenant_context.actor_user_id,
                    query_key: None,
                    "p_active_only": True,
                },
            )[: _limit(limits, max_attr, 5)]
            for row in rows:
                records.append(
                    _record(
                        category="organisation",
                        source_table=f"ovos.{table}",
                        source_ref=str(row.get("id") or ""),
                        title=str(row.get(title_field) or table),
                        summary=_safe_row_summary(
                            row, exclude={"id", "tenant_id", "owner_user_id"}
                        ),
                        confidence=_confidence(row),
                        sensitivity=str(row.get("visibility") or "private"),
                        observed_at=str(
                            row.get("updated_at") or row.get("created_at") or ""
                        ),
                        evidence_refs=_evidence(row, f"ovos.{table}"),
                    )
                )
        return records

    def _rpc_rows(
        self,
        name: str,
        payload: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], ...]:
        cache_key = json.dumps(
            {"rpc": name, "payload": dict(payload)},
            sort_keys=True,
        )
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.supabase_url}/rest/v1/rpc/{name}",
            data=body,
            headers={
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "hermes-agent-executive-context-repository/1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:
                raw = response.read()
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise ExecutiveContextRepositoryError(
                f"Executive Context RPC {name} unavailable"
            ) from exc
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else []
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExecutiveContextRepositoryError(
                f"Executive Context RPC {name} returned invalid JSON"
            ) from exc
        if not isinstance(parsed, list):
            raise ExecutiveContextRepositoryError(
                f"Executive Context RPC {name} returned invalid shape"
            )
        rows = tuple(row for row in parsed if isinstance(row, Mapping))
        self._request_cache[cache_key] = rows
        return rows

    def _load_strategic_records(
        self, tenant_context: TenantContext, limits: Any
    ) -> list[ExecutiveContextRecord]:
        records: list[ExecutiveContextRecord] = []
        for row in self._table_rows(
            "ede_executive_plans",
            {"tenant_id": tenant_context.tenant_id},
            limit=_limit(limits, "max_decisions", 5),
            order="updated_at.desc.nullslast,created_at.desc",
        ):
            records.append(
                _record(
                    category="strategic",
                    source_table="ovos.ede_executive_plans",
                    source_ref=str(row.get("id") or ""),
                    title=str(row.get("title") or "Executive plan"),
                    summary=_safe_row_summary(
                        row, exclude={"id", "tenant_id", "owner_user_id"}
                    ),
                    confidence=_confidence(row),
                    observed_at=str(
                        row.get("updated_at") or row.get("created_at") or ""
                    ),
                    evidence_refs=_evidence(row, "ovos.ede_executive_plans"),
                )
            )
        return records

    def _load_operational_records(
        self, tenant_context: TenantContext, limits: Any
    ) -> list[ExecutiveContextRecord]:
        records: list[ExecutiveContextRecord] = []
        for table, category_limit in (
            ("conversation_signals", "max_execution_requests"),
            ("ede_plan_risks", "max_risks"),
            ("ede_approval_requests", "max_approvals"),
            ("ede_execution_requests", "max_execution_requests"),
            ("executive_event_journal", "max_journal_records"),
        ):
            filters = {"tenant_id": tenant_context.tenant_id}
            if table == "conversation_signals":
                filters["owner_user_id"] = tenant_context.actor_user_id
                filters["status"] = "active"
            rows = self._table_rows(
                table,
                filters,
                limit=_limit(limits, category_limit, 5),
                order="created_at.desc",
            )
            for row in rows:
                records.append(
                    _record(
                        category="operational",
                        source_table=f"ovos.{table}",
                        source_ref=str(row.get("id") or row.get("event_id") or ""),
                        title=str(
                            row.get("title")
                            or row.get("signal_type")
                            or row.get("action_type")
                            or table
                        ),
                        summary=_safe_row_summary(
                            row, exclude={"id", "tenant_id", "owner_user_id"}
                        ),
                        confidence=_confidence(row),
                        sensitivity=str(
                            row.get("sensitivity")
                            or row.get("visibility")
                            or "internal"
                        ),
                        observed_at=str(
                            row.get("occurred_at")
                            or row.get("updated_at")
                            or row.get("created_at")
                            or ""
                        ),
                        evidence_refs=_evidence(row, f"ovos.{table}"),
                    )
                )
        return records

    def _load_governance_records(
        self, tenant_context: TenantContext, environment: str | None
    ) -> list[ExecutiveContextRecord]:
        evaluator = CapabilityTruthEvaluator(self.governance_repository)
        records = [
            _capability_record(
                evaluator.evaluate(tenant_context, key, environment=environment)
            )
            for key in DEFAULT_CAPABILITY_KEYS
        ]
        try:
            status = self.governance_repository.status(
                tenant_context, environment=environment
            )
        except GovernanceRepositoryError:
            status = {"proposal_counts": {}, "proposal_summaries": []}
        records.append(_proposal_status_record(status))
        return records

    def _load_knowledge_records(
        self, tenant_context: TenantContext, limits: Any
    ) -> list[ExecutiveContextRecord]:
        records: list[ExecutiveContextRecord] = []
        for table in ("knowledge_memories", "knowledge_objects"):
            rows = self._table_rows(
                table,
                {
                    "tenant_id": tenant_context.tenant_id,
                    "owner_user_id": tenant_context.actor_user_id,
                },
                limit=_limit(limits, "max_brief_items", 5),
                order="updated_at.desc.nullslast,created_at.desc",
            )
            for row in rows:
                records.append(
                    _record(
                        category="knowledge",
                        source_table=f"ovos.{table}",
                        source_ref=str(row.get("id") or ""),
                        title=str(row.get("title") or row.get("headline") or table),
                        summary=_safe_row_summary(
                            row,
                            exclude={
                                "id",
                                "tenant_id",
                                "owner_user_id",
                                "raw_content",
                                "content",
                            },
                        ),
                        confidence=_confidence(row),
                        sensitivity=str(row.get("visibility") or "internal"),
                        observed_at=str(
                            row.get("updated_at") or row.get("created_at") or ""
                        ),
                        evidence_refs=_evidence(row, f"ovos.{table}"),
                    )
                )
        return records

    def _table_rows(
        self,
        table: str,
        filters: Mapping[str, str],
        *,
        limit: int,
        order: str,
    ) -> tuple[Mapping[str, Any], ...]:
        cache_key = json.dumps(
            {"table": table, "filters": dict(filters), "limit": limit, "order": order},
            sort_keys=True,
        )
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]
        query: dict[str, str] = {
            "select": "*",
            "limit": str(max(0, limit)),
            "order": order,
        }
        for key, value in filters.items():
            query[key] = f"eq.{value}"
        url = f"{self.supabase_url}/rest/v1/{urllib.parse.quote(table)}?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(
            url,
            headers={
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._bearer_token}",
                "Accept-Profile": "ovos",
                "Accept": "application/json",
                "User-Agent": "hermes-agent-executive-context-repository/1",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 406:
                self._load_warnings.append(f"postgrest_schema_unavailable:{table}")
                self._request_cache[cache_key] = ()
                return ()
            raise ExecutiveContextRepositoryError(
                f"Executive Context table {table} unavailable"
            ) from exc
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise ExecutiveContextRepositoryError(
                f"Executive Context table {table} unavailable"
            ) from exc
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else []
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExecutiveContextRepositoryError(
                f"Executive Context table {table} returned invalid JSON"
            ) from exc
        if not isinstance(parsed, list):
            raise ExecutiveContextRepositoryError(
                f"Executive Context table {table} returned invalid shape"
            )
        rows = tuple(row for row in parsed if isinstance(row, Mapping))
        self._request_cache[cache_key] = rows
        return rows


class ExecutiveContextResolver:
    def __init__(self, *, repository: ExecutiveContextRepository | None = None) -> None:
        self.repository = repository or _default_repository()

    def resolve(
        self,
        *,
        turn: Any,
        request_classification: str,
        correlation_id: str,
        limits: Any,
        environment: str | None = None,
    ) -> ExecutiveContext:
        tenant_context, auth_state, warnings = self._resolve_tenant_context(
            turn, correlation_id
        )
        try:
            context = self.repository.load(
                tenant_context=tenant_context,
                actor_id=str(turn.actor_id or tenant_context.actor_user_id),
                request_classification=request_classification,
                correlation_id=correlation_id,
                limits=limits,
                environment=environment,
            )
        except ExecutiveContextRepositoryError:
            return _degraded_context(
                tenant_context=tenant_context,
                actor_id=str(turn.actor_id or tenant_context.actor_user_id),
                request_classification=request_classification,
                correlation_id=correlation_id,
                warnings=(*warnings, "executive_context_repository_unavailable"),
                authentication_state=auth_state,
            )
        identity = ExecutiveContextIdentity(
            tenant_id=context.identity.tenant_id,
            actor_id=context.identity.actor_id,
            actor_user_id=context.identity.actor_user_id,
            membership_id=context.identity.membership_id,
            role=context.identity.role,
            channel=context.identity.channel,
            actor_type=context.identity.actor_type,
            authentication_state=auth_state,
        )
        return ExecutiveContext(
            version=context.version,
            correlation_id=context.correlation_id,
            request_classification=context.request_classification,
            identity=identity,
            organisation=context.organisation,
            strategic=context.strategic,
            operational=context.operational,
            governance=context.governance,
            knowledge=context.knowledge,
            evidence_refs=context.evidence_refs,
            warnings=(*warnings, *context.warnings),
            degraded=context.degraded,
            generated_at=context.generated_at,
        )

    def _resolve_tenant_context(
        self, turn: Any, correlation_id: str
    ) -> tuple[TenantContext, str, tuple[str, ...]]:
        try:
            context = TenantContextResolver().resolve(
                channel=str(turn.platform or "gateway"),
                actor_type="human",
                correlation_id=correlation_id,
            )
            return context, "supabase_auth_configured", ()
        except GovernanceConfigurationError:
            tenant_id = str(turn.tenant_id or "")
            actor_id = str(turn.actor_id or "")
            actor_user_id = actor_id if _is_uuid(actor_id) else None
            context = TenantContext(
                user_id=actor_user_id,
                tenant_id=tenant_id,
                role="runtime_authenticated_actor",
                channel=str(turn.platform or "gateway"),
                actor_type="human",
                correlation_id=correlation_id,
            )
            return (
                context,
                "runtime_gateway_authenticated_degraded",
                ("configured_supabase_auth_context_unavailable",),
            )


def _default_repository() -> ExecutiveContextRepository:
    try:
        return SupabaseExecutiveContextRepository.from_environment()
    except GovernanceConfigurationError:
        return InMemoryExecutiveContextRepository(available=False)


def _build_context_from_records(
    *,
    tenant_context: TenantContext,
    actor_id: str,
    request_classification: str,
    correlation_id: str,
    records: tuple[ExecutiveContextRecord, ...],
    limits: Any,
    warnings: tuple[str, ...],
    degraded: bool,
) -> ExecutiveContext:
    identity = ExecutiveContextIdentity(
        tenant_id=tenant_context.tenant_id,
        actor_id=actor_id,
        actor_user_id=tenant_context.user_id,
        membership_id=tenant_context.membership_id,
        role=tenant_context.role,
        channel=tenant_context.channel,
        actor_type=tenant_context.actor_type,
        authentication_state="resolved",
    )
    deduped = _limit_records(
        _dedupe_records(tuple(_ensure_record_evidence(record) for record in records)),
        limits,
    )
    evidence = tuple(
        dict.fromkeys(
            evidence for record in deduped for evidence in record.evidence_refs
        )
    )
    return ExecutiveContext(
        version=EXECUTIVE_CONTEXT_VERSION,
        correlation_id=correlation_id,
        request_classification=request_classification,
        identity=identity,
        organisation=tuple(
            record
            for record in deduped
            if record.category in {"identity", "organisation"}
        ),
        strategic=tuple(record for record in deduped if record.category == "strategic"),
        operational=tuple(
            record for record in deduped if record.category == "operational"
        ),
        governance=tuple(
            record for record in deduped if record.category == "governance"
        ),
        knowledge=tuple(record for record in deduped if record.category == "knowledge"),
        evidence_refs=evidence,
        warnings=warnings,
        degraded=degraded,
    )


def _degraded_context(
    *,
    tenant_context: TenantContext,
    actor_id: str,
    request_classification: str,
    correlation_id: str,
    warnings: tuple[str, ...],
    authentication_state: str,
) -> ExecutiveContext:
    identity = ExecutiveContextIdentity(
        tenant_id=tenant_context.tenant_id,
        actor_id=actor_id,
        actor_user_id=tenant_context.user_id,
        membership_id=tenant_context.membership_id,
        role=tenant_context.role,
        channel=tenant_context.channel,
        actor_type=tenant_context.actor_type,
        authentication_state=authentication_state,
    )
    return ExecutiveContext(
        version=EXECUTIVE_CONTEXT_VERSION,
        correlation_id=correlation_id,
        request_classification=request_classification,
        identity=identity,
        governance=(
            ExecutiveContextRecord(
                record_id=f"governance:degraded:{correlation_id}",
                category="governance",
                source_table="hermes.runtime",
                source_ref="executive_context_repository_unavailable",
                title="Executive Context Repository unavailable",
                summary=(
                    "Authoritative EDP context could not be loaded; context "
                    "is degraded and execution remains not_executed."
                ),
                confidence=1.0,
                sensitivity="internal",
                observed_at=_now_iso(),
            ),
        ),
        warnings=warnings,
        degraded=True,
    )


def _capability_record(truth: Any) -> ExecutiveContextRecord:
    summary = (
        f"capability_key={truth.capability_key} code_ceiling={truth.code_ceiling} "
        f"database_overlay={truth.database_overlay or 'none'} "
        f"effective_state={truth.effective_state} reason={truth.reason}"
    )
    return ExecutiveContextRecord(
        record_id=f"governance:capability:{truth.capability_key}",
        category="governance",
        source_table="ovos.edp_capability_overlays",
        source_ref=truth.capability_key,
        title=f"Capability Truth: {truth.capability_key}",
        summary=summary,
        confidence=1.0,
        sensitivity="internal",
        observed_at=_now_iso(),
        evidence_refs=(
            ExecutiveContextEvidence(
                evidence_id=f"capability:{truth.capability_key}",
                source_table="ovos.edp_capability_overlays",
                source_ref=truth.capability_key,
                digest=_digest(summary)[:16],
            ),
        ),
    )


def _proposal_status_record(status: Mapping[str, Any]) -> ExecutiveContextRecord:
    counts = status.get("proposal_counts") or {}
    summaries = status.get("proposal_summaries") or []
    summary = (
        f"proposal_counts={json.dumps(counts, sort_keys=True)} "
        f"bounded_summary_count={len(summaries) if isinstance(summaries, list) else 0} "
        "direct_mutation_performed=false execution_status=not_executed"
    )
    return ExecutiveContextRecord(
        record_id="governance:improvement_proposals:status",
        category="governance",
        source_table="ovos.edp_improvement_proposals",
        source_ref="status",
        title="Improvement Proposal status",
        summary=summary,
        confidence=1.0,
        sensitivity="internal",
        observed_at=_now_iso(),
        evidence_refs=(
            ExecutiveContextEvidence(
                evidence_id="improvement_proposals:status",
                source_table="ovos.edp_improvement_proposals",
                source_ref="status",
                digest=_digest(summary)[:16],
            ),
        ),
    )


def _record(**kwargs: Any) -> ExecutiveContextRecord:
    return ExecutiveContextRecord(
        record_id=f"{kwargs['source_table']}:{kwargs['source_ref']}",
        **kwargs,
    )


def _dedupe_records(
    records: tuple[ExecutiveContextRecord, ...],
) -> tuple[ExecutiveContextRecord, ...]:
    seen: set[str] = set()
    deduped: list[ExecutiveContextRecord] = []
    for record in records:
        key = _digest(
            "|".join((
                record.category,
                record.source_table,
                record.source_ref,
                record.title,
                record.summary,
            ))
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return tuple(deduped)


def _ensure_record_evidence(record: ExecutiveContextRecord) -> ExecutiveContextRecord:
    if record.evidence_refs:
        return record
    evidence = ExecutiveContextEvidence(
        evidence_id=f"{record.source_table}:id:{record.source_ref}",
        source_table=record.source_table,
        source_ref=record.source_ref,
        digest=_digest(f"{record.source_table}:{record.source_ref}")[:16],
        sensitivity=record.sensitivity,
    )
    return replace(record, evidence_refs=(evidence,))


def _limit_records(
    records: tuple[ExecutiveContextRecord, ...],
    limits: Any,
) -> tuple[ExecutiveContextRecord, ...]:
    per_category = {
        "identity": 2,
        "organisation": max(
            _limit(limits, "max_brief_items", 5),
            _limit(limits, "max_decisions", 5),
        ),
        "strategic": _limit(limits, "max_decisions", 5),
        "operational": (
            _limit(limits, "max_journal_records", 5)
            + _limit(limits, "max_approvals", 5)
            + _limit(limits, "max_execution_requests", 5)
            + _limit(limits, "max_risks", 5)
            + _limit(limits, "max_opportunities", 5)
        ),
        "governance": 32,
        "knowledge": _limit(limits, "max_brief_items", 5),
    }
    counts: dict[str, int] = {}
    selected: list[ExecutiveContextRecord] = []
    for record in records:
        limit = per_category.get(record.category, _limit(limits, "max_brief_items", 5))
        used = counts.get(record.category, 0)
        if used >= limit:
            continue
        counts[record.category] = used + 1
        selected.append(record)
    return tuple(selected)


def _evidence(
    row: Mapping[str, Any], source_table: str
) -> tuple[ExecutiveContextEvidence, ...]:
    refs = []
    for key in (
        "source_record_id",
        "knowledge_object_id",
        "event_id",
        "brief_id",
        "id",
    ):
        value = str(row.get(key) or "")
        if value:
            refs.append(
                ExecutiveContextEvidence(
                    evidence_id=f"{source_table}:{key}:{value}",
                    source_table=source_table,
                    source_ref=value,
                    digest=_digest(value)[:16],
                    sensitivity=str(
                        row.get("sensitivity") or row.get("visibility") or "internal"
                    ),
                )
            )
    return tuple(refs)


def _safe_row_summary(row: Mapping[str, Any], *, exclude: set[str]) -> str:
    parts: list[str] = []
    for key, value in sorted(row.items()):
        if key in exclude or value in (None, "", [], {}):
            continue
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, sort_keys=True)[:240]
        else:
            rendered = str(value)[:240]
        parts.append(f"{key}={_redact_secrets(rendered)}")
        if len(parts) >= 8:
            break
    return "; ".join(parts) or "metadata available"


def _join_summary(**values: Any) -> str:
    parts = []
    for key, value in values.items():
        if value:
            parts.append(f"{key}={_redact_secrets(str(value))[:320]}")
    return "; ".join(parts) or "organisation metadata available"


def _json_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:5])
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return ", ".join(str(item) for item in parsed[:5])
        except json.JSONDecodeError:
            return value
    return ""


def _confidence(row: Mapping[str, Any]) -> float:
    try:
        return float(row.get("confidence") or 1.0)
    except (TypeError, ValueError):
        return 1.0


def _limit(limits: Any, name: str, default: int) -> int:
    try:
        return max(0, int(getattr(limits, name, default)))
    except (TypeError, ValueError):
        return default


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


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*=\s*\S+"),
    re.compile(r"(?i)(bearer)\s+[A-Za-z0-9._-]+"),
)


def _redact_secrets(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _safe_label(value: str | None) -> str:
    return _redact_secrets(str(value or "unknown"))[:160]
