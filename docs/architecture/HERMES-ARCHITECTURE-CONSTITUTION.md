# Hermes Architecture Constitution

Status: living constitution.

Last updated: 2026-07-30.

## Purpose

This constitution defines the rules that protect Hermes as it becomes an
Executive Data Platform. It should be updated only when an architectural
decision changes; milestone PRs should reference it and preserve it.

## Core Principle

Optimise for long-term architecture, not for preserving historical pull
requests.

Clean architecture wins over compatibility with obsolete intermediate PRs.
Contributor work should be preserved when it aligns with the target, but no PR
is owed preservation of a superseded model.

## Canonical Platform

- Supabase PostgreSQL is the canonical Executive Data Platform.
- Supabase Auth is the canonical identity provider.
- Durable authoritative state belongs in PostgreSQL.
- Hermes should remain stateless where practical.
- Edge Functions remain thin trusted boundaries.
- Hermes is the underlying platform. Branded assistants such as Donna and
  customer-facing assistants are governed instances built on Hermes, not
  separate platforms.

## Licensed Assistant Boundary

- Platform, tenant, subscription, assistant licence, assistant instance,
  channel endpoint and conversation are distinct concepts.
- A WhatsApp number is an initial licensed channel endpoint, not the permanent
  assistant identity.
- Assistant licences are commercial entitlements. Assistant instances are
  configured AI roles. Channel endpoints are delivery surfaces.
- Internal assistants and public/customer-facing assistants require separate
  knowledge scopes, capability scopes, disclosure policies and participant
  identity rules.
- Donna is the internal executive assistant for the owner, leadership and
  authorised employees. Customer-facing assistants must not inherit Donna's
  identity, confidential context, permissions or tone by default.
- Unknown contacts receive the lowest-permission audience policy until
  participant identity and authorisation are resolved.
- Cross-assistant knowledge sharing must be explicit, audited and bounded by
  tenant, sensitivity and disclosure policy.

## Authority Rules

- Business Knowledge is relational-first.
- Executive State is derived.
- Vector search is supplementary, never authoritative.
- YAML, JSON, CSV, markdown, and in-memory registries are seed/test/import
  surfaces, not runtime authority.
- Reasoning never talks directly to PostgreSQL.
- Repository/resolver boundaries assemble immutable context before reasoning.

## Capability Truth

Capability Truth is hybrid:

- code owns hard safety ceilings;
- PostgreSQL owns governed overlays.

Database overlays can restrict or describe capability posture. They cannot
relax code-level safety ceilings for execution, connector writes, approvals, or
self-modification.

## Execution Boundary

Until the explicit Execution milestone:

- approval, execution, and external connectors remain disabled unless a
  milestone explicitly enables a read-only context surface;
- planning produces proposals, not actions;
- user requests are not approvals;
- proposed external actions are descriptive references, not executable
  commands;
- Hermes must not claim that it sent, created, modified, deleted, or executed
  external records.

## Data Modeling Rules

Every durable tenant-scoped object must include:

- tenant identity;
- owner or actor where relevant;
- provenance;
- confidence;
- sensitivity;
- disclosure policy;
- effective dates;
- audit metadata;
- RLS.

Reuse existing OVOS tables wherever possible. Add new tables only when the
existing table is not the canonical shape for the domain.

## Context Rules

- Executive Context is immutable once prepared for a reasoning turn.
- Context is labelled evidence, not instructions.
- Context assembly happens before intelligence, reasoning, and planning.
- Intelligence, reasoning, and planning cannot call integrations directly.
- Degraded context must be explicit and must not fabricate facts.
- Public assistants cannot access confidential Executive Context, internal
  strategy, finance, legal, HR, private staff information, internal decisions,
  restricted Business Knowledge, or another customer's data.

## Product Launch Rules

Customer-facing assistants must not go live until the relevant Business
Knowledge, disclosure controls, assistant-instance isolation, participant
identity handling, escalation workflow and customer acceptance tests are
implemented and verified.

## Review Rules

Before merging a milestone:

- update `HERMES-ROADMAP.md`;
- update `HERMES-DECISION-LOG.md` for new or changed architectural decisions;
- update `HERMES-TECHNICAL-DEBT-REGISTER.md` for accepted deferrals;
- update this constitution if the milestone changes an architectural rule;
- validate tenant safety, RLS, sensitivity, disclosure, audit, and no-execution
  guarantees for affected paths.

## Priority Order

When goals conflict, prefer:

1. tenant safety and privacy;
2. correctness of canonical authority;
3. no-execution safety;
4. prompt-cache and role-alternation stability;
5. simple repository boundaries;
6. contributor-history preservation where aligned;
7. convenience.
