from __future__ import annotations

from gateway.business_knowledge import (
    BusinessKnowledgeIngestionRequest,
    BusinessKnowledgeRegistry,
    BusinessKnowledgeRetriever,
    BusinessKnowledgeRecord,
    ingest_business_knowledge,
)


def test_ingestion_creates_proposed_facts_requiring_owner_review() -> None:
    result = ingest_business_knowledge(
        BusinessKnowledgeIngestionRequest(
            tenant_id="tenant-1",
            owner_user_id="owner-1",
            source_type="markdown",
            source_reference="bootstrap.md",
            raw_content="- Om Vidya Group owns RoboThink UK.\n- Secret lease dispute.",
        )
    )

    assert result.publication_status == "owner_review_required"
    assert result.proposed_fact_count == 2
    assert all(fact.verification_status == "proposed" for fact in result.proposed_facts)
    assert all(
        fact.publication_status == "not_published" for fact in result.proposed_facts
    )


def test_retrieval_filters_tenant_user_sensitivity_and_disclosure_channel() -> None:
    registry = BusinessKnowledgeRegistry()
    registry.add_record(
        BusinessKnowledgeRecord(
            record_id="rec-ovg",
            tenant_id="tenant-1",
            entity_type="Group",
            canonical_name="Om Vidya Group",
            summary="Owner-confirmed education group context.",
            source_type="owner_import",
            source_reference="organisation.yaml",
            source_authority="owner_confirmed",
            confidence="high",
            verification_status="verified",
            sensitivity="internal",
            disclosure_policy="owner_safe",
            created_by="owner-1",
        )
    )
    registry.add_record(
        BusinessKnowledgeRecord(
            record_id="rec-secret",
            tenant_id="tenant-1",
            entity_type="Risk",
            canonical_name="Lease dispute",
            summary="Restricted legal matter.",
            source_type="owner_import",
            source_reference="restricted.yaml",
            source_authority="owner_confirmed",
            confidence="medium",
            verification_status="verified",
            sensitivity="restricted",
            disclosure_policy="never_disclose",
            created_by="owner-1",
        )
    )
    registry.add_record(
        BusinessKnowledgeRecord(
            record_id="rec-other",
            tenant_id="tenant-2",
            entity_type="Group",
            canonical_name="Other Group",
            summary="Must not leak.",
            source_type="owner_import",
            source_reference="other.yaml",
            source_authority="owner_confirmed",
            confidence="high",
            verification_status="verified",
            sensitivity="internal",
            disclosure_policy="owner_safe",
            created_by="owner-2",
        )
    )

    result = BusinessKnowledgeRetriever(registry).retrieve(
        tenant_id="tenant-1",
        user_id="owner-1",
        request_purpose="executive_status",
        disclosure_channel="whatsapp",
        query="Om Vidya Group priorities",
    )

    assert [item.record_id for item in result.items] == ["rec-ovg"]
    assert result.safe_context_items[0].source == "business_knowledge"
    assert "rec-secret" not in str(result.safe_context_items)
    assert "Must not leak" not in str(result.safe_context_items)


def test_conflicts_and_stale_facts_are_not_silently_treated_as_current() -> None:
    registry = BusinessKnowledgeRegistry()
    for revenue, record_id in (("£100k MRR", "rec-a"), ("£250k MRR", "rec-b")):
        registry.add_record(
            BusinessKnowledgeRecord(
                record_id=record_id,
                tenant_id="tenant-1",
                entity_type="FinancialMetric",
                canonical_name="Monthly revenue",
                summary=revenue,
                source_type="import",
                source_reference=f"{record_id}.yaml",
                source_authority="owner_import",
                confidence="medium",
                verification_status="verified",
                sensitivity="confidential",
                disclosure_policy="internal_reasoning_only",
                created_by="owner-1",
                conflict_group_id="mrr",
            )
        )
    registry.add_record(
        BusinessKnowledgeRecord(
            record_id="rec-stale",
            tenant_id="tenant-1",
            entity_type="KPI",
            canonical_name="Old growth target",
            summary="Outdated target.",
            source_type="import",
            source_reference="old.yaml",
            source_authority="owner_import",
            confidence="low",
            verification_status="verified",
            sensitivity="internal",
            disclosure_policy="owner_safe",
            created_by="owner-1",
            effective_to="2025-12-31",
        )
    )

    result = BusinessKnowledgeRetriever(registry).retrieve(
        tenant_id="tenant-1",
        user_id="owner-1",
        request_purpose="planning",
        disclosure_channel="internal_reasoning",
        query="monthly revenue growth target",
    )

    assert result.conflicts
    assert result.stale_record_ids == ("rec-stale",)
    assert all(item.confidence != "high" for item in result.items)
