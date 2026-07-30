# ADR-0004: Relational-First Business Knowledge

Status: proposed

Decision: Business Knowledge is relational-first, with JSONB only for bounded
extensions and versioned payloads.

Consequences:

- facts, entities, evidence, sensitivity, confidence, and disclosure policy are
  queryable and governable;
- vector search is supplementary;
- YAML and in-memory registries are seed/test abstractions, not production
  authority.
