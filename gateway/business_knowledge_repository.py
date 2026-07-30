"""Business Knowledge repository boundary for Executive Context.

Slice 3 keeps Business Knowledge authoritative in OVOS/Supabase PostgreSQL.
This module exposes typed repository contracts and a resolver that turns
tenant-scoped business entities, facts, and evidence into immutable Executive
Context records. It does not parse local YAML/JSON/CSV files, run ingestion
pipelines, call connectors, or execute external actions.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from gateway.edp_governance import TenantContext


BUSINESS_KNOWLEDGE_SOURCE = "ovos_postgresql"
IMPORT_ONLY_FORMATS = frozenset({"yaml", "json", "csv"})


class BusinessKnowledgeRepositoryError(RuntimeError):
    """Raised when the Business Knowledge repository cannot load safely."""


@dataclass(frozen=True)
class BusinessKnowledgeEvidence:
    evidence_id: str
    source_ref: str
    title: str
    summary: str
    confidence: float = 1.0
    sensitivity: str = "internal"
    digest: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BusinessKnowledgeEntity:
    entity_id: str
    entity_kind: str
    canonical_name: str
    summary: str
    status: str
    confidence: float = 0.5
    sensitivity: str = "internal"
    source_ref: str | None = None
    observed_at: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BusinessKnowledgeFact:
    fact_id: str
    fact_type: str
    fact_label: str
    statement: str
    lifecycle: str
    confidence: float = 0.5
    sensitivity: str = "internal"
    source_ref: str | None = None
    observed_at: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BusinessKnowledgeSnapshot:
    entities: tuple[BusinessKnowledgeEntity, ...] = ()
    facts: tuple[BusinessKnowledgeFact, ...] = ()
    evidence: tuple[BusinessKnowledgeEvidence, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def source_counts(self) -> Mapping[str, int]:
        return {
            "business_entities": len(self.entities),
            "business_facts": len(self.facts),
            "business_evidence": len(self.evidence),
        }


class BusinessEntityRepository(Protocol):
    def search_entities(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        entity_kinds: Sequence[str] | None = None,
        include_sensitive: bool = False,
        limit: int = 10,
    ) -> tuple[BusinessKnowledgeEntity, ...]: ...


class BusinessFactRepository(Protocol):
    def search_facts(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        fact_types: Sequence[str] | None = None,
        lifecycles: Sequence[str] = ("verified", "proposed"),
        include_sensitive: bool = False,
        limit: int = 25,
    ) -> tuple[BusinessKnowledgeFact, ...]: ...


class EvidenceRepository(Protocol):
    def list_evidence(
        self,
        *,
        tenant_context: TenantContext,
        fact_id: str | None = None,
        include_sensitive: bool = False,
    ) -> tuple[BusinessKnowledgeEvidence, ...]: ...


class BusinessKnowledgeRepository(
    BusinessEntityRepository,
    BusinessFactRepository,
    EvidenceRepository,
    Protocol,
):
    def dry_run_import(
        self,
        *,
        tenant_context: TenantContext,
        source_format: str,
        source_name: str,
        items: Sequence[Mapping[str, Any]],
        provenance: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Mapping[str, Any]: ...


class InMemoryBusinessKnowledgeRepository:
    """Test double. Runtime authority remains PostgreSQL-backed."""

    def __init__(
        self,
        *,
        entities: Sequence[BusinessKnowledgeEntity] = (),
        facts: Sequence[BusinessKnowledgeFact] = (),
        evidence: Sequence[BusinessKnowledgeEvidence] = (),
        available: bool = True,
    ) -> None:
        self.entities = tuple(entities)
        self.facts = tuple(facts)
        self.evidence = tuple(evidence)
        self.available = available
        self.import_calls: list[Mapping[str, Any]] = []

    def search_entities(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        entity_kinds: Sequence[str] | None = None,
        include_sensitive: bool = False,
        limit: int = 10,
    ) -> tuple[BusinessKnowledgeEntity, ...]:
        del tenant_context
        if not self.available:
            raise BusinessKnowledgeRepositoryError("business entity repository unavailable")
        rows = [
            entity
            for entity in self.entities
            if _matches(query, entity.canonical_name, entity.summary)
            and (entity_kinds is None or entity.entity_kind in entity_kinds)
            and (include_sensitive or entity.sensitivity in {"public", "internal"})
        ]
        return tuple(rows[:limit])

    def search_facts(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        fact_types: Sequence[str] | None = None,
        lifecycles: Sequence[str] = ("verified", "proposed"),
        include_sensitive: bool = False,
        limit: int = 25,
    ) -> tuple[BusinessKnowledgeFact, ...]:
        del tenant_context
        if not self.available:
            raise BusinessKnowledgeRepositoryError("business fact repository unavailable")
        rows = [
            fact
            for fact in self.facts
            if _matches(query, fact.fact_label, fact.statement)
            and (fact_types is None or fact.fact_type in fact_types)
            and fact.lifecycle in lifecycles
            and (include_sensitive or fact.sensitivity in {"public", "internal"})
        ]
        return tuple(rows[:limit])

    def list_evidence(
        self,
        *,
        tenant_context: TenantContext,
        fact_id: str | None = None,
        include_sensitive: bool = False,
    ) -> tuple[BusinessKnowledgeEvidence, ...]:
        del tenant_context, fact_id
        if not self.available:
            raise BusinessKnowledgeRepositoryError("evidence repository unavailable")
        return tuple(
            evidence
            for evidence in self.evidence
            if include_sensitive or evidence.sensitivity in {"public", "internal"}
        )

    def dry_run_import(
        self,
        *,
        tenant_context: TenantContext,
        source_format: str,
        source_name: str,
        items: Sequence[Mapping[str, Any]],
        provenance: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Mapping[str, Any]:
        _validate_import_format(source_format)
        call = {
            "tenant_id": tenant_context.tenant_id,
            "actor_user_id": tenant_context.actor_user_id,
            "source_format": source_format,
            "source_name": source_name,
            "items": tuple(dict(item) for item in items),
            "provenance": dict(provenance or {}),
            "correlation_id": correlation_id,
        }
        self.import_calls.append(call)
        return {
            "runtime_authority": False,
            "execution_status": "not_executed",
            "candidate_count": len(items),
            "duplicate_count": 0,
            "conflict_count": 0,
            "source": BUSINESS_KNOWLEDGE_SOURCE,
        }


class SupabaseBusinessKnowledgeRepository:
    """Public-RPC-backed Business Knowledge repository."""

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
        self._request_cache: dict[str, tuple[Mapping[str, Any], ...]] = {}

    def search_entities(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        entity_kinds: Sequence[str] | None = None,
        include_sensitive: bool = False,
        limit: int = 10,
    ) -> tuple[BusinessKnowledgeEntity, ...]:
        del limit
        rows = self._rpc_rows(
            "ovos_bk_search_entities",
            {
                "p_tenant_id": tenant_context.tenant_id,
                "p_owner_user_id": tenant_context.actor_user_id,
                "p_query": query,
                "p_entity_kinds": list(entity_kinds) if entity_kinds else None,
                "p_include_sensitive": include_sensitive,
                "p_active_only": True,
            },
        )
        return tuple(_entity_from_row(row) for row in rows)

    def search_facts(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        fact_types: Sequence[str] | None = None,
        lifecycles: Sequence[str] = ("verified", "proposed"),
        include_sensitive: bool = False,
        limit: int = 25,
    ) -> tuple[BusinessKnowledgeFact, ...]:
        rows = self._rpc_rows(
            "ovos_bk_search_facts",
            {
                "p_tenant_id": tenant_context.tenant_id,
                "p_owner_user_id": tenant_context.actor_user_id,
                "p_query": query,
                "p_fact_types": list(fact_types) if fact_types else None,
                "p_lifecycles": list(lifecycles),
                "p_include_sensitive": include_sensitive,
                "p_limit": limit,
            },
        )
        return tuple(_fact_from_row(row) for row in rows)

    def list_evidence(
        self,
        *,
        tenant_context: TenantContext,
        fact_id: str | None = None,
        include_sensitive: bool = False,
    ) -> tuple[BusinessKnowledgeEvidence, ...]:
        rows = self._rpc_rows(
            "ovos_bk_list_evidence",
            {
                "p_tenant_id": tenant_context.tenant_id,
                "p_owner_user_id": tenant_context.actor_user_id,
                "p_fact_id": fact_id,
                "p_include_sensitive": include_sensitive,
            },
        )
        return tuple(_evidence_from_row(row) for row in rows)

    def dry_run_import(
        self,
        *,
        tenant_context: TenantContext,
        source_format: str,
        source_name: str,
        items: Sequence[Mapping[str, Any]],
        provenance: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Mapping[str, Any]:
        _validate_import_format(source_format)
        payload = {
            "tenant_id": tenant_context.tenant_id,
            "actor_user_id": tenant_context.actor_user_id,
            "source_format": source_format,
            "source_name": source_name,
            "payload_digest": _payload_digest(items),
            "items": [dict(item) for item in items],
            "provenance": {
                **dict(provenance or {}),
                "import_only": True,
                "runtime_authority": False,
            },
            "correlation_id": correlation_id,
        }
        result = self._rpc_json("ovos_bk_import_dry_run", payload)
        return {
            **result,
            "runtime_authority": False,
            "execution_status": "not_executed",
        }

    def _rpc_rows(
        self,
        name: str,
        payload: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], ...]:
        cache_key = json.dumps(
            {"rpc": name, "payload": payload},
            sort_keys=True,
        )
        if cache_key in self._request_cache:
            return self._request_cache[cache_key]
        result = self._rpc_json(name, payload)
        if isinstance(result, list):
            rows = tuple(row for row in result if isinstance(row, Mapping))
            self._request_cache[cache_key] = rows
            return rows
        raise BusinessKnowledgeRepositoryError(
            f"Business Knowledge RPC {name} returned invalid shape"
        )

    def _rpc_json(self, name: str, payload: Mapping[str, Any]) -> Any:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            f"{self.supabase_url}/rest/v1/rpc/{name}",
            data=body,
            headers={
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "hermes-agent-business-knowledge-repository/1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self._timeout_seconds
            ) as response:
                raw = response.read()
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise BusinessKnowledgeRepositoryError(
                f"Business Knowledge RPC {name} unavailable"
            ) from exc
        try:
            return json.loads(raw.decode("utf-8")) if raw else []
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BusinessKnowledgeRepositoryError(
                f"Business Knowledge RPC {name} returned invalid JSON"
            ) from exc


class BusinessKnowledgeResolver:
    def __init__(self, *, repository: BusinessKnowledgeRepository) -> None:
        self.repository = repository

    def resolve(
        self,
        *,
        tenant_context: TenantContext,
        query: str | None = None,
        include_sensitive: bool = False,
        limit: int = 10,
    ) -> BusinessKnowledgeSnapshot:
        try:
            entities = self.repository.search_entities(
                tenant_context=tenant_context,
                query=query,
                include_sensitive=include_sensitive,
                limit=limit,
            )
            facts = self.repository.search_facts(
                tenant_context=tenant_context,
                query=query,
                include_sensitive=include_sensitive,
                limit=max(limit, 25),
            )
            evidence = self.repository.list_evidence(
                tenant_context=tenant_context,
                include_sensitive=False,
            )
        except BusinessKnowledgeRepositoryError:
            return BusinessKnowledgeSnapshot(
                warnings=("business_knowledge_repository_unavailable",)
            )
        return BusinessKnowledgeSnapshot(
            entities=entities,
            facts=facts,
            evidence=evidence,
        )


def _entity_from_row(row: Mapping[str, Any]) -> BusinessKnowledgeEntity:
    return BusinessKnowledgeEntity(
        entity_id=str(row.get("entity_id") or ""),
        entity_kind=str(row.get("entity_kind") or "unknown"),
        canonical_name=str(row.get("canonical_name") or "Business entity"),
        summary=str(row.get("summary") or ""),
        status=str(row.get("status") or "unknown"),
        confidence=_confidence(row),
        sensitivity=str(row.get("sensitivity") or "internal"),
        source_ref=str(row.get("source_evidence_id") or row.get("source_record_id") or ""),
        observed_at=str(row.get("updated_at") or row.get("created_at") or ""),
        provenance=_mapping(row.get("provenance")),
    )


def _fact_from_row(row: Mapping[str, Any]) -> BusinessKnowledgeFact:
    return BusinessKnowledgeFact(
        fact_id=str(row.get("fact_id") or ""),
        fact_type=str(row.get("fact_type") or "general"),
        fact_label=str(row.get("fact_label") or "Business fact"),
        statement=str(row.get("normalized_statement") or row.get("fact_value") or ""),
        lifecycle=str(row.get("lifecycle") or "proposed"),
        confidence=_confidence(row),
        sensitivity=str(row.get("sensitivity") or "internal"),
        source_ref=str(row.get("source_evidence_id") or ""),
        observed_at=str(row.get("updated_at") or row.get("created_at") or ""),
        provenance=_mapping(row.get("provenance")),
    )


def _evidence_from_row(row: Mapping[str, Any]) -> BusinessKnowledgeEvidence:
    return BusinessKnowledgeEvidence(
        evidence_id=str(row.get("evidence_id") or ""),
        source_ref=str(row.get("evidence_ref") or row.get("source_id") or ""),
        title=str(row.get("title") or "Business evidence"),
        summary=str(row.get("summary") or ""),
        confidence=_confidence(row),
        sensitivity=str(row.get("sensitivity") or "internal"),
        digest=str(row.get("evidence_digest") or "") or None,
        provenance=_mapping(row.get("provenance")),
    )


def _validate_import_format(source_format: str) -> None:
    if source_format not in IMPORT_ONLY_FORMATS:
        raise ValueError("Business Knowledge imports must be YAML, JSON, or CSV")


def _payload_digest(items: Sequence[Mapping[str, Any]]) -> str:
    canonical = json.dumps([dict(item) for item in items], sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _confidence(row: Mapping[str, Any]) -> float:
    try:
        return max(0.0, min(1.0, float(row.get("confidence", 0.5))))
    except (TypeError, ValueError):
        return 0.5


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _matches(query: str | None, *values: str) -> bool:
    if not query:
        return True
    needle = query.casefold()
    return any(needle in value.casefold() for value in values)
