# Hermes Data And State Inventory v1

Status: architecture inventory. Metadata only. No secrets or private row data
are included.

## Current State Mechanisms

### Supabase / `ovos-core`

`ovos-core` contains 17 migrations through `20260729130000`. The migrations
define the `ovos` application schema, 102 distinct application tables, 48
functions, 92 indexes, 33 triggers, and 88 RLS policies according to a static
migration parse. The schema is not exposed through the local Supabase Data API
configuration.

Major persisted domains:

- capture and knowledge core: `knowledge_objects`, `source_records`,
  `attachments`, `relationships`, `processing_events`;
- conversation provenance: `conversations`, `conversation_participants`,
  `conversation_messages`, `conversation_signals`, `conversation_summaries`;
- evidence and memory: `knowledge_memories`, `evidence_items`,
  `evidence_source_links`;
- executive context: executive identities, organisation contexts, team members,
  team capabilities, responsibility assignments;
- EDE foundation, reasoning, organisational knowledge graph, pattern evolution,
  planning/approval, execution safety kernel;
- Hermes MVP event journal and daily briefs.

### `hermes-agent`

Current durable or semi-durable mechanisms:

- SQLite `state.db`: canonical local session metadata, transcripts, FTS indexes,
  message counts, model usage, gateway routing, compression locks, async
  delegations, handoff state, Telegram topic bindings, and maintenance state.
- `sessions/sessions.json`: routing/session metadata cache and legacy fallback.
- `executive_orchestrator_traces.jsonl`: local privacy-preserving orchestrator
  trace stream.
- `config.yaml` and `.env`: runtime configuration and feature flags.
- `auth.json` and provider token files: authentication state and credentials.
- Markdown memories/profile files: `memories/USER.md`, `SOUL.md`, skill files.
- Local SQLite/JSON systems: `kanban.db`, `cron/executions.db`,
  `gateway_state.json`, channel directory, cache JSON files, model catalogs,
  WhatsApp session files and logs.
- In-memory registries in PR #18: capability truth, business knowledge, planning
  and governance proposal objects.

### VPS Runtime

Read-only inspection observed:

- running Hermes gateway Python process;
- WhatsApp bridge child process;
- LiteLLM on port 4000;
- no matching `hermes-gateway.service` unit visible through `systemctl`;
- no relevant active Docker containers from the inspected `docker ps`;
- local Hermes state under `/home/hermes/.hermes`;
- Supabase environment variable names in `/opt/ai-stack/ovos-core/.env.supabase`
  only, with values not printed.

## Inventory Table

| data_object | current_owner | current_location | format | authority | scope | sensitivity | auditability | known risk | proposed_future_home |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| users | partial Supabase/Auth | Auth plus UUID columns | Auth/JWT/UUID | incomplete | tenant/user | high | partial | no single Hermes user table | `identity.users` plus Auth linkage |
| tenants | implicit | UUID columns in `ovos` | UUID | weak | tenant | high | partial | no canonical tenant lifecycle | `identity.tenants` |
| tenant memberships | implicit | RLS and app config | policy/config | weak | tenant/user | high | partial | app/service-role may bypass intended roles | `identity.tenant_memberships` |
| organisations | `ovos-core` | organisation context tables | relational/JSONB | partial | tenant/user | medium/high | versioned partly | context tables mix profile and org facts | `organisation.organisations` |
| legal entities | not explicit | business context text | text/JSONB | absent | tenant | high | weak | legal distinctions unavailable | `organisation.legal_entities` |
| brands | partial | context fields, EDE payloads | arrays/JSONB | weak | tenant | medium | partial | no canonical brand IDs | `organisation.brands` |
| people | partial | team members, participants, source records | relational/text | partial | tenant/user | high | partial | phone/email can leak if traces dump raw rows | `organisation.people` plus contact points |
| roles | partial | team roles, EDE role definitions, PR #18 governance | relational/code | duplicated | tenant/user | medium | partial | code and DB concepts diverge | `identity.roles`, `identity.permissions`, `organisation.business_roles` |
| relationships | `ovos-core` | `ovos.relationships`, OKG edges | relational | partial | tenant | medium | versioned partly | multiple edge systems | `organisation.relationships` and `knowledge.relationships` |
| programmes/products/locations | partial | org context arrays/EDE objects | arrays/JSONB | weak | tenant | medium | partial | not queryable as canonical entities | `organisation.programmes`, `products`, `locations` |
| objectives/priorities/projects/initiatives | EDE/planning | EDE objects/plans/local PR #18 planning | relational/in-memory | partial | tenant/user | medium/high | partial | local planning abstractions may compete | `executive.objectives`, `priorities`, `initiatives`, `projects` |
| KPIs/financial metrics | not explicit | possible text facts | text/JSONB | absent | tenant | high | weak | unsupported executive state claims | `executive.kpis`, `metric_observations` |
| decisions | EDE | reasoning/planning/event journal tables | relational | partial | tenant/user | high | good for EDE | no unified decision read model | `executive.decisions` |
| risks | EDE/planning | plan risks, event journal | relational | partial | tenant/user | high | partial | risk statements can be ungrounded | `executive.risks` with evidence links |
| commitments | conversation signals | signals, EDE/event journal | relational | partial | tenant/user | medium/high | partial | no canonical current commitments view | `executive.commitments` |
| meetings | conversation only | messages/signals | text/JSONB | weak | tenant/user | high | partial | no Calendar connector or calendar facts | future `integration.calendar_events_readonly` plus executive read model |
| documents | `ovos-core` partial | storage bucket plus attachments/evidence | object/relational | partial | tenant/user | high | partial | remote bucket size policy mismatch | `documents.documents`, versions, chunks |
| document chunks | not explicit | none detected | none | absent | tenant/user | high | absent | vector retrieval not designed | `documents.document_chunks` |
| embeddings | not explicit | Supabase storage vector enabled, no table | none/qdrant dir | absent | tenant/user | high | absent | no governed pgvector metadata | `documents.embeddings` |
| business facts | EDE/context | knowledge objects/memories/EDE objects | relational/JSONB | partial | tenant/user | medium/high | partial | facts not uniformly versioned or reviewed | `knowledge.business_facts`, `fact_versions` |
| evidence/provenance/confidence | `ovos-core` | evidence/source/context tables | relational/JSONB | partial | tenant/user | medium/high | good base | not yet universal | `knowledge.evidence`, `sources` |
| sensitivity/disclosure policy | partial/PR #18 | visibility fields, governance code | enum/code | duplicated | tenant/user/channel | high | partial | code-only disclosure decisions not durable | `governance.disclosure_policies`, `disclosure_decisions` |
| sessions/messages | `hermes-agent` | local `state.db`, `sessions.json` | SQLite/JSON | authoritative local | user/channel | high | local only | host-local source of truth | staged Postgres conversation store or replicated summaries |
| context snapshots | Orchestrator | local JSONL, runtime metadata | JSONL | derived | tenant/conversation | high | local only | not durable across host loss | `audit.context_retrieved`, `executive.context_snapshots` |
| intelligence/reasoning outputs | EDE plus Orchestrator | Supabase EDE tables, local trace JSONL | relational/JSONL | duplicated | tenant/user | high | mixed | partial local-only traces | `audit.model_invocations`, EDE read models |
| planning requests/candidate plans/steps | EDE | EDE planning tables, PR #18 planning | relational/in-memory | partial | tenant/user | high | good in EDE | PR #18 local planning should not persist | `planning.*` backed by existing EDE tables or migrated schemas |
| approval requirements/approvals | EDE | EDE approval tables | relational | partial | tenant/user | high | good | no future UX boundary yet | `planning.approval_requirements`, `governance.approval_records` |
| execution requests/receipts/outcomes | EDE safety | EDE 007A tables | relational | authoritative non-executing | tenant/user | very high | good | must remain non-executable | `governance.proposed_external_actions`, receipts only after future execution |
| capability truth | PR #18/code | code registry | code/in-memory | baseline only | tenant/channel | high | weak | connector discussions may diverge from reality | hybrid code baseline plus `governance.capability_truth` |
| connection/authorisation state | env/local tokens | `.env`, `auth.json`, token files | env/JSON | fragmented | user/system | secret | weak | secrets on host, no tenant records | secrets vault plus `integration.connections`, `authorisations` metadata |
| self-improvement proposals | PR #18 | in-memory/report only | Python objects | proposal-only | system | medium | weak | can be lost or accidentally applied later | `governance.improvement_proposals` |
| audit events/state transitions/security events | mixed | EDE tables, local logs, JSONL | relational/log/JSONL | fragmented | tenant/system | high | partial | logs used as state | `audit.audit_events`, `state_transitions`, `security_events` |
| system configuration/feature flags | `hermes-agent` | `.env`, `config.yaml` | env/YAML | local | system | secret/high | weak | not tenant-aware or auditable | local secrets plus `system.feature_flags` metadata |

## Duplicated Or Competing Sources

- Conversation state exists in `state.db`, `sessions.json`, runtime memory, and
  partial Supabase conversation provenance.
- Executive traces exist in local JSONL and related EDE/event-journal tables.
- Organisation/business context exists in Supabase context tables, EDE objects,
  Markdown memories, PR #18 YAML, and PR #18 in-memory registry.
- Capability truth exists in environment/config, code, runtime connector state,
  and PR #18 deterministic registry.
- Planning concepts exist in EDE planning tables and PR #18 local planning
  objects.

## State With No Reliable Source Of Truth

- Legal entities, products, programmes, customer segments, partner records,
  financial metrics, document chunks, embeddings, and future dashboard/mobile
  preferences.

## State That Should Never Be Persisted

- Full system prompts, hidden reasoning, secrets, OAuth refresh tokens in
  business tables, full raw connector payloads without retention need, and raw
  private message dumps in audit events.

## PR #18 Objects That Need PostgreSQL

- capability truth overlays;
- disclosure decisions and policy outcomes;
- improvement proposals;
- business knowledge records;
- planning context snapshots where they survive a turn;
- governance CLI audit records.
