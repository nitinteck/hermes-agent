# Hermes Decision Log

Status: living decision log.

Last updated: 2026-08-01.

## Maintenance Rule

Every milestone PR must add or update entries here when it makes, reverses, or
clarifies an architectural decision. Link detailed ADRs where they exist.

## Decisions

| id | date | decision | status | consequence |
| --- | --- | --- | --- | --- |
| HDL-0001 | 2026-07-30 | Supabase PostgreSQL is the canonical Executive Data Platform. | accepted | Durable authoritative EDP state lives in PostgreSQL, not local files or runtime memory. |
| HDL-0002 | 2026-07-30 | Supabase Auth is the canonical identity provider. | accepted | Tenant/user authorization must map to Supabase Auth and RLS. |
| HDL-0003 | 2026-07-30 | Hermes should remain stateless where practical. | accepted | Runtime components assemble context and proposals but do not own durable authority. |
| HDL-0004 | 2026-07-30 | Use selective event sourcing. | accepted | Audit and lifecycle events are durable where useful; not every read model is event-sourced. |
| HDL-0005 | 2026-07-30 | Capability Truth is hybrid. | accepted | Code owns hard ceilings; PostgreSQL owns governed overlays. |
| HDL-0006 | 2026-07-30 | Business Knowledge is relational-first. | accepted | Facts, entities, evidence, confidence, sensitivity, and disclosure are queryable relational records. |
| HDL-0007 | 2026-07-30 | Vector search is supplementary. | accepted | Vectors can assist retrieval later but cannot become source of truth. |
| HDL-0008 | 2026-07-30 | Executive State is derived. | accepted | State snapshots/read models must be computed from authoritative sources. |
| HDL-0009 | 2026-07-30 | Edge Functions remain thin trusted boundaries. | accepted | Business authority and complex orchestration stay in database/repository layers. |
| HDL-0010 | 2026-07-30 | Approval, execution, and external connectors remain disabled until explicit milestones. | accepted | Planning and proposal features cannot smuggle in live execution. |
| HDL-0011 | 2026-07-30 | PR #18 should not be preserved as historical architecture. | accepted | Only aligned governance/IP/planning/context-continuity ideas were salvaged; obsolete local authority was rejected. |
| HDL-0012 | 2026-07-30 | PostgREST access to private `ovos` schema should not be assumed. | accepted | Runtime reads use deliberate public RPCs for private-schema data. |
| HDL-0013 | 2026-07-30 | YAML, JSON, and CSV are import-only surfaces. | accepted | They may create dry-run candidates but are never runtime authority. |
| HDL-0014 | 2026-07-30 | Every future milestone updates roadmap, constitution, decision log, and technical debt register. | accepted | Documentation maintenance is part of milestone completion, not after-the-fact cleanup. |
| HDL-0015 | 2026-07-30 | RC1 runtime feature development is frozen during owner WhatsApp validation. | accepted | OVOS PR #14 and Hermes PR #25 remain open/unmerged; no Business Knowledge migration, deployment, connectors, approvals, or execution during RC1 testing. |
| HDL-0016 | 2026-07-30 | Hermes is the platform; Donna is the internal executive assistant instance. | accepted | Customer-facing assistants must not share Donna's identity, confidential context or internal permissions by default. |
| HDL-0017 | 2026-07-30 | Licensed assistant architecture separates tenant, subscription, assistant licence, assistant instance, endpoint and conversation. | accepted | WhatsApp numbers are licensed endpoints, not permanent assistant identities or tenant boundaries. |
| HDL-0018 | 2026-07-30 | Public assistants require disclosure, participant identity and assistant-instance isolation before launch. | accepted | Parent Assistant remains future work and cannot go live from RC1 or frozen Business Knowledge PRs alone. |
| HDL-0019 | 2026-07-30 | The next candidate post-RC1 milestone is Donna Executive Conversation Engine. | accepted | Improve planning intent, working set, evidence-led answers, truthfulness and refusal quality without external capabilities. |
| HDL-0020 | 2026-07-30 | Conversation Engine is a request-time orchestration layer, not durable state. | accepted | Working sets are transient, tenant/user bound and reconstructable from bounded recent context. |
| HDL-0021 | 2026-07-30 | Execution truthfulness is enforced after reasoning and before emission. | accepted | Completed-action claims are rewritten unless a verified execution receipt exists. |
| HDL-0022 | 2026-07-30 | PR #27 is not merged wholesale for Donna Conversation Engine v1. | accepted | Compatible safety ideas are reused; planning registry expansion remains deferred and PR #27 stays open. |
| HDL-0023 | 2026-08-01 | Donna RC1 runs with a deterministic, channel-specific tool allowlist (`donna_owner_rc1`) instead of the generic upstream Hermes toolset. | accepted | Terminal, shell/subprocess, `execute_code`, `write_file`, `patch`, `skill_manage`, browser automation and `computer_use` are never presented to or invocable by the model for a Donna WhatsApp turn; the restriction is scoped to the Executive Orchestrator route and does not remove these tools from other Hermes platforms/profiles. |

## Pending Decisions

| id | decision needed | target milestone | notes |
| --- | --- | --- | --- |
| HDL-P001 | How Business Knowledge Population review/promotion is operated. | Business Knowledge Population | Needs owner-approved import/review workflow without ingestion pipeline or execution. |
| HDL-P002 | Hybrid Retrieval ranking contract. | Hybrid Retrieval | Must keep relational filters authoritative before vector search. |
| HDL-P003 | Executive State freshness and derivation contract. | Executive State | Must prove read model is derived and traceable to evidence. |
| HDL-P004 | Read-only connector order and data minimisation. | Calendar/ClickUp/Gmail | Calendar is currently roadmapped before ClickUp and Gmail. |
| HDL-P005 | Approval record semantics. | Approvals | User requests are not approvals; approval records need explicit actor, scope, expiry, and replay protections. |
| HDL-P006 | Execution receipt and rollback semantics. | Execution | Execution must be separately authorised, idempotent, auditable, and unable to fabricate receipts. |
| HDL-P007 | Subscription and licence persistence shape. | Multi-Assistant Product Foundation | Product model is documented only; implementation must reuse existing tenant/auth patterns. |
| HDL-P008 | Public assistant escalation workflow. | Multi-Assistant Product Foundation | Parent Assistant needs safe handoff without exposing internal executive context. |
| HDL-P009 | Durable conversation working-set persistence, if any. | Future Conversation Engine | v1 is transient; any persistence must not become Executive State or hidden memory. |

## Reversal Rule

Reversing a decision requires:

- a new entry with the superseding decision;
- a migration or runtime impact note;
- an explicit statement of what old behavior must not be preserved.
