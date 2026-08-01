# Hermes Business Knowledge Domain Model v1

Status: Slice 3 review candidate.

## Tables

| table | purpose |
| --- | --- |
| `ovos.business_sources` | canonical source system references linked to existing OVOS source records where available |
| `ovos.business_evidence` | evidence metadata, digest, summary, confidence, sensitivity, and verification status |
| `ovos.business_entities` | canonical business objects using `entity_kind` for organisation, brand, person, product, project, risk, KPI, and related kinds |
| `ovos.business_entity_relationships` | typed relationships between canonical business entities |
| `ovos.business_facts` | lifecycle-managed assertions about entities or the business |
| `ovos.business_fact_evidence` | many-to-many evidence links with support/contradiction semantics |
| `ovos.business_reviews` | review outcomes for facts, entities, evidence, sources, and import candidates |
| `ovos.business_import_batches` | durable dry-run records for YAML, JSON, and CSV candidate batches |
| `ovos.business_import_candidates` | candidate rows with duplicate/conflict status; never runtime authority |

## Entity Kinds

`business_entities.entity_kind` supports:

- `organisation`, `brand`, `legal_entity`;
- `person`, `role`, `relationship`, `location`;
- `product`, `programme`;
- `objective`, `project`, `initiative`;
- `decision`, `risk`, `commitment`, `kpi`.

The table is intentionally canonical and generic. Specific user interfaces can
project a brand, person, risk, or KPI view from the same table without creating
parallel entities.

## Common Governance Columns

Every Slice 3 durable table includes:

- `tenant_id`;
- `owner_user_id`;
- `provenance`;
- `confidence`;
- `sensitivity`;
- `disclosure_policy`;
- `effective_from`;
- `effective_to`;
- `created_by`;
- `updated_by`;
- `created_at`;
- `updated_at`.

Reviewable tables also include reviewer fields such as `verified_by`,
`reviewed_by`, `reviewed_at`, `review_status`, or lifecycle review notes.

## Reuse

Business Knowledge references existing OVOS records instead of replacing them:

- `source_record_id` links back to captured message/file/source metadata;
- `knowledge_object_id` links back to captured knowledge objects;
- `source_evidence_id` links canonical entities and facts to evidence rows;
- audit is recorded through `ovos.edp_record_governance_audit`, which writes
  bounded events to `ovos.executive_event_journal`.
