# Hermes Business Knowledge Foundation v1

Status: Slice 3 review candidate.

## Purpose

Business Knowledge is the canonical relational model for durable business facts
and entities in the Executive Data Platform. It answers "what is true about the
business, and why do we believe it?" without deriving Executive State, building
vectors, ingesting files, or executing external actions.

## Boundaries

In scope:

- organisations, brands, legal entities, people, roles, relationships,
  locations, products, programmes, objectives, projects, initiatives,
  decisions, risks, commitments, and KPIs;
- business facts with lifecycle, confidence, sensitivity, disclosure policy,
  provenance, evidence, verification, and review;
- import-only dry-run records for YAML, JSON, and CSV candidate payloads;
- tenant-scoped RLS and bounded audit through the existing EDP journal.

Out of scope:

- Executive State snapshots or current-state derivation;
- vector indexes, embeddings, or retrieval ranking;
- ingestion pipelines, connector sync, file parsing, or background import jobs;
- approval, execution, connector writes, or external mutations.

## Canonical Authority

Durable authority lives in Supabase PostgreSQL under private `ovos` tables.
Runtime reads go through public OVOS RPCs. Hermes reasoning receives immutable
Executive Context records assembled by repositories; it never talks directly to
PostgreSQL and never treats YAML, JSON, CSV, or local files as authority.

Existing OVOS tables remain source/provenance surfaces:

- `ovos.source_records`;
- `ovos.knowledge_objects`;
- `ovos.relationships`;
- `ovos.executive_event_journal`;
- existing Executive Context tables such as `organisation_contexts`,
  `team_members`, and `responsibility_assignments`.

Slice 3 adds canonical Business Knowledge tables rather than duplicating those
capture tables.

## Review Criteria

- every durable table has tenant, owner, provenance, confidence, sensitivity,
  disclosure policy, effective dates, audit fields, and RLS;
- public RPCs include tenant and owner filters;
- imports are dry-run/import-only and return `runtime_authority=false`;
- lifecycle transitions are explicit and audited;
- Executive Context consumes Business Knowledge through a repository/resolver;
- no code path introduces execution, vectors, Executive State, or YAML runtime
  authority.
