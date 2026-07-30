# Hermes Hybrid Retrieval v1

Status: target design.

## Recommendation

Use relational-first hybrid retrieval. Verified facts, relationships, decisions,
plans, KPIs, and permissions come from PostgreSQL. Vector search supplements
recall over document chunks and long-form evidence; it never decides truth,
access, or action eligibility.

## Retrieval Pipeline

1. Classify request and actor/channel.
2. Determine allowed source categories and sensitivity levels.
3. Retrieve canonical relational facts and current executive read models.
4. Retrieve graph/entity relationships where relevant.
5. Retrieve document chunks using keyword and vector search with tenant and
   sensitivity filters.
6. Rank by relevance, freshness, confidence, and evidence quality.
7. Resolve conflicts by preferring verified/current records and surfacing
   disputed or stale state.
8. Return bounded context with evidence references and source categories.

## Embedding Ownership

Embeddings are owned by `documents.embeddings` or `knowledge.fact_embeddings`.
Each row should include:

- `tenant_id`;
- linked chunk or fact id;
- embedding model and version;
- source text digest, not full text where avoidable;
- chunking strategy version;
- generated_at;
- freshness/staleness;
- sensitivity;
- deletion status.

## Filtering Rules

- Tenant filtering is mandatory.
- Sensitivity/disclosure filtering must happen before model context assembly.
- Vector similarity cannot override RLS.
- Deleted or redacted documents must propagate deletion to chunks and embeddings.
- Freshness matters for commitments, meetings, KPIs, risks, and capability
  truth.
- Every retrieved item must carry provenance and a safe evidence reference.

## Conflict Handling

If vector search returns text that conflicts with a verified relational fact,
Hermes should either use the verified fact or tell the user that the evidence is
conflicting. It must not silently blend stale text into a current executive
claim.
