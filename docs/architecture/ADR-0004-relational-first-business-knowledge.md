# ADR-0004: Relational-First Business Knowledge

Status: accepted for Slice 3

Decision: Business Knowledge is relational-first, with JSONB only for bounded
extensions and versioned payloads.

Consequences:

- facts, entities, evidence, sensitivity, confidence, and disclosure policy are
  queryable and governable;
- vector search is supplementary;
- YAML and in-memory registries are seed/test abstractions, not production
  authority.

Slice 3 implements this decision through private `ovos.business_*` tables and
public read/dry-run RPCs. Runtime reasoning consumes Business Knowledge only via
`BusinessKnowledgeRepository`, `BusinessKnowledgeResolver`, and the
`ExecutiveContextRepository` boundary.
