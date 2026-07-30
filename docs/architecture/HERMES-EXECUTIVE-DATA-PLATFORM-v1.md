# Hermes Executive Data Platform v1

Status: architecture blueprint. No migration has been applied, deployed, or
enabled.

This document defines the target durable data architecture for Hermes before
new connectors, approval capabilities, execution capabilities, or persistent
autonomous behaviour are added.

## Evidence Base

- `ovos-core` local `main`: `0e6ee394d26ff2d7a814f3c84e0ed920aaaf5232`
- `hermes-agent` open PR #18 head inspected: `78a8e7913ef831801b8dad3634dee1d14b9ffee7`
- VPS read-only deployed SHAs observed:
  - `hermes-agent`: `e48afa71693dfbde08448b4a92e0038384773053`
  - `ovos-core`: `0e6ee394d26ff2d7a814f3c84e0ed920aaaf5232`
- Supabase project visible from CLI: `OVOS`, ref `fpzmvmzxzpkybooileua`, region
  West Europe.
- Local Supabase migrations current through
  `20260729130000_hermes_mvp_event_journal_daily_brief.sql`.
- Remote Edge Functions list returned no deployed functions.
- Remote Storage metadata showed one private bucket, `ovos-private`.

See [HERMES-SUPABASE-CURRENT-STATE-AUDIT-v1.md](../operations/HERMES-SUPABASE-CURRENT-STATE-AUDIT-v1.md)
and [HERMES-DATA-AND-STATE-INVENTORY-v1.md](HERMES-DATA-AND-STATE-INVENTORY-v1.md)
for the inventory behind these conclusions.

## Decisive Architecture

Hermes should treat Supabase PostgreSQL as the canonical Executive Data
Platform for durable business, governance, planning, approval, audit, evidence,
capability, integration, and executive-state records. Hermes runtime services
should become progressively more stateless and should retain orchestration,
reasoning, context assembly, policy evaluation, and temporary request-local
computation rather than durable source-of-truth state.

Supabase is not merely attachment storage. It should become the governed system
of record for what Hermes knows, why it believes it, who may see it, what can be
acted on, and what happened.

## Layer A: Supabase Executive Data Platform

| Capability | Responsibility |
| --- | --- |
| PostgreSQL | Canonical relational state, lifecycle records, evidence metadata, current read models, version history, audit events, capability truth, connection state, approval state, proposed actions, receipts, and bounded model invocation metadata. |
| Auth | Human identity, session identity, future dashboard/mobile auth, tenant membership claims, MFA policy where needed. |
| RLS | Non-bypassable tenant, owner, role, brand, sensitivity, document, vector, and approval boundaries. Application filters are defence in depth, not the security boundary. |
| Storage | Private object storage for source files, rendered documents, attachments, extraction artifacts, and evidence binaries. PostgreSQL owns metadata, lifecycle, sensitivity, and access policy. |
| pgvector | Supplementary semantic retrieval over chunks and facts, always filtered by tenant, sensitivity, freshness, and disclosure policy. Never source of truth. |
| Realtime | Dashboard/operator subscriptions for approval queues, plan lifecycle, risk state, and health. Avoid internal orchestration over Realtime. |
| Queues/pgmq | Retryable asynchronous jobs: document ingestion, embeddings, scheduled evaluations, connector sync, outcome checks, stale-fact reviews. |
| Cron | Stale knowledge detection, executive-state snapshots, overdue commitments, expiring authorisations, metric aggregation, retention jobs, health checks. |
| Edge Functions | Thin trusted boundary for OAuth callbacks, signed webhook verification, upload initiation, approval link validation, lightweight event ingestion, and queue publication. Not a reasoning or workflow engine. |

## Layer B: Hermes Runtime

Hermes Python services should retain:

- transport-specific inbound handling and outbound delivery;
- executive orchestration and context assembly;
- deterministic capability invocation for local safe capabilities;
- EDE shadow/advisory processing;
- model-provider interaction;
- reasoning and response construction;
- planning and policy evaluation;
- safety validation and execution prohibition;
- connector orchestration once connectors exist;
- request-local temporary computation.

Hermes must not retain independent durable sources of truth for:

- business facts and organisational context;
- capability truth and connector availability;
- approvals, authorisations, execution eligibility, or receipts;
- business knowledge registries;
- self-improvement proposals;
- event-journal records and executive traces that must survive host loss;
- document metadata and embedding metadata;
- executive-state read models.

Local files may remain for runtime configuration, secrets, WhatsApp transport
session material, caches, and development-only skill/profile material until
each category has a deliberate migration plan.

## Layer C: Integration Boundary

Future connectors should enter the platform through explicit integration
records:

- inbound event stored first as immutable, idempotent metadata;
- raw payload redacted, hashed, or stored in private object storage only when
  retention is justified;
- connection and authorisation state stored separately from capability truth;
- proposed external action recorded declaratively before any execution path;
- approval and safety state checked by PostgreSQL-backed policies and the
  Execution Safety Kernel;
- execution receipts stored after future controlled execution, never invented
  by the model.

For WhatsApp, Gmail, Google Calendar, ClickUp, Slack, CRM, webhooks, and future
systems, knowledge availability must not imply disclosure permission or action
permission.

## Layer D: User And Operator Experiences

| Experience | Data boundary |
| --- | --- |
| Normal WhatsApp | Narrow conversational response surface. Reads only context selected by Hermes and allowed for the actor/channel. No raw dumps, no unapproved disclosure, no execution. |
| Future executive dashboard | Tenant-authenticated read/write interface over approved read models and approval queues. RLS and policy decisions must still apply. |
| Future mobile interface | Same as dashboard with stricter session/device policy and smaller disclosure surface. |
| Secure operator CLI | Diagnostics, migrations, health, trace lookup, and administrative review. Must avoid private row dumps and broad service-role mutation. |
| Administrative interface | Tenant, role, policy, retention, and connector management with auditable operator actions. |
| Approval interface | Human approval recording only. Approval must not itself execute external actions. |

## Non-Persisted Data

Hermes should never persist:

- API keys, OAuth refresh tokens, or service-role tokens outside the approved
  secrets mechanism;
- full private prompts as audit payloads;
- raw system prompts in user-visible traces;
- chain-of-thought or hidden reasoning;
- complete connector payloads when a minimal evidence reference is sufficient;
- cross-tenant search material;
- external-action claims not backed by a future execution receipt;
- volatile model/tool scratch state.

## Immediate Architectural Risks

1. `hermes-agent` currently keeps important state in local `state.db`,
   `sessions.json`, Markdown memory/profile files, JSONL traces, caches, and
   token/config files. These are not governed by Supabase RLS.
2. The Executive Orchestrator trace sink writes JSONL locally. This is useful
   during rollout but not sufficient as the durable executive audit record.
3. PR #18 introduces in-memory and YAML-backed business/governance concepts that
   should not become competing sources of truth.
4. The VPS process model is unclear: a gateway process was observed, but no
   `hermes-gateway.service` unit was discoverable in the read-only inspection.
5. The VPS `ovos-core` checkout was observed ahead of `origin/main`, which makes
   production/source parity hard to reason about.
6. The Supabase schema has many tenant/user columns and RLS policies, but there
   is not yet a clear canonical identity/tenant/membership foundation across all
   Hermes state.

## Recommendation

Proceed to Executive Data Platform implementation planning before merging
additional business-context or connector functionality. PR #18 can remain a
governance hardening PR, but it should not be treated as the durable data
platform. See [HERMES-PR18-EDP-ALIGNMENT-REVIEW-v1.md](HERMES-PR18-EDP-ALIGNMENT-REVIEW-v1.md)
for required pre-merge clarifications.

Next implementation milestone:

`HERMES EXECUTIVE DATA PLATFORM STAGE 0/1 - TENANCY, RLS, AUDIT AND GOVERNANCE FOUNDATION`
