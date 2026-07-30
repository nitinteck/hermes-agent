"""Governed business knowledge contracts for Hermes executive context."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from gateway.executive_orchestrator import ContextItem


ENTITY_TYPES = {
    "Group",
    "LegalEntity",
    "Brand",
    "Person",
    "Role",
    "Location",
    "Programme",
    "Product",
    "CustomerSegment",
    "Partner",
    "Project",
    "Objective",
    "KPI",
    "Policy",
    "Contract",
    "Risk",
    "Decision",
    "FinancialMetric",
    "OperatingConstraint",
    "Relationship",
    "Initiative",
}

VISIBLE_POLICIES = {"public_summary", "owner_safe"}
INTERNAL_POLICIES = {*VISIBLE_POLICIES, "internal_reasoning_only"}


@dataclass(frozen=True)
class BusinessKnowledgeRecord:
    record_id: str
    tenant_id: str
    entity_type: str
    canonical_name: str
    summary: str
    source_type: str
    source_reference: str
    source_authority: str
    confidence: str
    verification_status: str
    sensitivity: str
    disclosure_policy: str
    created_by: str
    aliases: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_to: str | None = None
    review_due: str | None = None
    lifecycle_state: str = "active"
    created_at: int = 0
    updated_at: int = 0
    supersedes_record_id: str | None = None
    conflict_group_id: str | None = None
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.entity_type not in ENTITY_TYPES:
            raise ValueError(
                f"unknown business knowledge entity type: {self.entity_type}"
            )
        if self.verification_status not in {
            "proposed",
            "verified",
            "disputed",
            "superseded",
            "expired",
        }:
            raise ValueError("invalid verification status")
        if self.sensitivity not in {
            "public",
            "internal",
            "confidential",
            "restricted",
            "secret",
        }:
            raise ValueError("invalid sensitivity")
        if self.disclosure_policy not in {
            "public_summary",
            "owner_safe",
            "internal_reasoning_only",
            "restricted_operator_only",
            "never_disclose",
        }:
            raise ValueError("invalid disclosure policy")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "record_id_digest": _digest(self.record_id)[:16],
            "entity_type": self.entity_type,
            "canonical_name_digest": _digest(self.canonical_name)[:16],
            "source_type": self.source_type,
            "source_authority": self.source_authority,
            "confidence": self.confidence,
            "verification_status": self.verification_status,
            "sensitivity": self.sensitivity,
            "disclosure_policy": self.disclosure_policy,
            "lifecycle_state": self.lifecycle_state,
        }


@dataclass(frozen=True)
class BusinessKnowledgeIngestionRequest:
    tenant_id: str
    owner_user_id: str
    source_type: str
    source_reference: str
    raw_content: str


@dataclass(frozen=True)
class ExtractedBusinessFact:
    fact_id: str
    tenant_id: str
    entity_type: str
    canonical_name: str
    summary: str
    source_type: str
    source_reference: str
    confidence: str = "low"
    verification_status: str = "proposed"
    publication_status: str = "not_published"
    owner_review_required: bool = True


@dataclass(frozen=True)
class KnowledgeConflict:
    conflict_group_id: str
    record_ids: tuple[str, ...]
    safe_message: str


@dataclass(frozen=True)
class KnowledgeReviewPackage:
    package_id: str
    proposed_facts: tuple[ExtractedBusinessFact, ...]
    conflicts: tuple[KnowledgeConflict, ...] = ()


@dataclass(frozen=True)
class KnowledgePublicationResult:
    publication_status: str
    proposed_facts: tuple[ExtractedBusinessFact, ...]
    review_package: KnowledgeReviewPackage

    @property
    def proposed_fact_count(self) -> int:
        return len(self.proposed_facts)


@dataclass(frozen=True)
class BusinessKnowledgeRetrievalResult:
    items: tuple[BusinessKnowledgeRecord, ...]
    safe_context_items: tuple[ContextItem, ...]
    conflicts: tuple[KnowledgeConflict, ...] = ()
    stale_record_ids: tuple[str, ...] = ()
    provenance: tuple[Mapping[str, Any], ...] = ()


class BusinessKnowledgeRegistry:
    def __init__(self) -> None:
        self._records: dict[str, BusinessKnowledgeRecord] = {}

    def add_record(self, record: BusinessKnowledgeRecord) -> None:
        now = int(time.time())
        if record.created_at == 0:
            record = replace(record, created_at=now, updated_at=now)
        self._records[record.record_id] = record

    def list_records(self) -> tuple[BusinessKnowledgeRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def status(self) -> dict[str, Any]:
        records = self.list_records()
        return {
            "enabled": True,
            "record_count": len(records),
            "verified_count": sum(
                1 for record in records if record.verification_status == "verified"
            ),
            "proposed_count": sum(
                1 for record in records if record.verification_status == "proposed"
            ),
            "restricted_retrieval_enabled": False,
            "redacted": True,
        }


class BusinessKnowledgeRetriever:
    def __init__(self, registry: BusinessKnowledgeRegistry) -> None:
        self.registry = registry

    def retrieve(
        self,
        *,
        tenant_id: str,
        user_id: str,
        request_purpose: str,
        disclosure_channel: str,
        query: str,
    ) -> BusinessKnowledgeRetrievalResult:
        del user_id, request_purpose
        records: list[BusinessKnowledgeRecord] = []
        stale: list[str] = []
        conflicts = _detect_conflicts(self.registry.list_records(), tenant_id)
        for record in self.registry.list_records():
            if record.tenant_id != tenant_id:
                continue
            if record.verification_status not in {"verified", "proposed"}:
                continue
            if _is_stale(record):
                stale.append(record.record_id)
                continue
            if not _allowed_for_channel(record, disclosure_channel):
                continue
            if not _relevant(record, query):
                continue
            lowered_confidence = (
                "medium"
                if record.conflict_group_id
                and any(
                    record.record_id in conflict.record_ids for conflict in conflicts
                )
                else record.confidence
            )
            records.append(replace(record, confidence=lowered_confidence))
        context_items = tuple(
            ContextItem(
                source="business_knowledge",
                reference_id=f"business_knowledge:{_digest(record.record_id)[:12]}",
                title=record.entity_type,
                summary=(
                    "Based on business information previously confirmed or staged "
                    f"for review: {record.canonical_name} - {record.summary}"
                ),
            )
            for record in records
        )
        return BusinessKnowledgeRetrievalResult(
            items=tuple(records),
            safe_context_items=context_items,
            conflicts=conflicts,
            stale_record_ids=tuple(stale),
            provenance=tuple(record.safe_trace() for record in records),
        )


def ingest_business_knowledge(
    request: BusinessKnowledgeIngestionRequest,
) -> KnowledgePublicationResult:
    facts: list[ExtractedBusinessFact] = []
    for index, line in enumerate(request.raw_content.splitlines(), start=1):
        text = line.strip(" -\t")
        if not text:
            continue
        entity_type = _infer_entity_type(text)
        canonical = _canonical_name(text)
        facts.append(
            ExtractedBusinessFact(
                fact_id=f"fact_{_digest(f'{request.source_reference}|{index}|{text}')[:16]}",
                tenant_id=request.tenant_id,
                entity_type=entity_type,
                canonical_name=canonical,
                summary=text[:400],
                source_type=request.source_type,
                source_reference=request.source_reference,
            )
        )
    package = KnowledgeReviewPackage(
        package_id=f"review_{_digest(request.source_reference + request.raw_content)[:16]}",
        proposed_facts=tuple(facts),
    )
    return KnowledgePublicationResult(
        publication_status="owner_review_required",
        proposed_facts=tuple(facts),
        review_package=package,
    )


def build_business_context_status() -> dict[str, Any]:
    return {
        "business_knowledge_registry_enabled": True,
        "business_context_ingestion_enabled": True,
        "business_context_retrieval_enabled": True,
        "restricted_context_retrieval_enabled": False,
        "publication_requires_owner_review": True,
        "redacted": True,
    }


def _allowed_for_channel(record: BusinessKnowledgeRecord, channel: str) -> bool:
    if record.disclosure_policy == "never_disclose":
        return False
    if record.sensitivity in {"restricted", "secret"}:
        return False
    if channel == "internal_reasoning":
        return record.disclosure_policy in INTERNAL_POLICIES
    return record.disclosure_policy in VISIBLE_POLICIES and record.sensitivity in {
        "public",
        "internal",
    }


def _relevant(record: BusinessKnowledgeRecord, query: str) -> bool:
    folded = query.casefold()
    terms = {
        term
        for text in (record.canonical_name, record.summary, *record.aliases)
        for term in re.findall(r"[a-z0-9£]+", text.casefold())
        if len(term) > 2
    }
    if not folded.strip():
        return True
    return any(term in folded for term in terms)


def _detect_conflicts(
    records: tuple[BusinessKnowledgeRecord, ...],
    tenant_id: str,
) -> tuple[KnowledgeConflict, ...]:
    groups: dict[str, list[str]] = {}
    for record in records:
        if record.tenant_id == tenant_id and record.conflict_group_id:
            groups.setdefault(record.conflict_group_id, []).append(record.record_id)
    return tuple(
        KnowledgeConflict(
            conflict_group_id=group_id,
            record_ids=tuple(record_ids),
            safe_message="Conflicting business facts require owner review.",
        )
        for group_id, record_ids in sorted(groups.items())
        if len(record_ids) > 1
    )


def _is_stale(record: BusinessKnowledgeRecord) -> bool:
    return bool(record.effective_to and record.effective_to < "2026-07-30")


def _infer_entity_type(text: str) -> str:
    folded = text.casefold()
    if "secret" in folded or "risk" in folded or "dispute" in folded:
        return "Risk"
    if "revenue" in folded or "mrr" in folded:
        return "FinancialMetric"
    if "brand" in folded or "robothink" in folded or "stem club" in folded:
        return "Brand"
    if "group" in folded or "limited" in folded:
        return "Group"
    return "Initiative"


def _canonical_name(text: str) -> str:
    match = re.match(r"([A-Z][A-Za-z0-9 &£.-]{2,60})", text)
    if match:
        return match.group(1).strip(" .")
    return text[:60]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
