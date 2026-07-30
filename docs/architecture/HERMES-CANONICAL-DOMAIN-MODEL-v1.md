# Hermes Canonical Domain Model v1

Status: target model. This is not a migration.

The model below favours canonical relational records with JSONB only for
bounded, versioned extension payloads. Existing `ovos` tables should be reused
or migrated incrementally where they already satisfy the contract.

## Schema Map

| schema | purpose |
| --- | --- |
| `identity` | tenants, users, memberships, roles, permissions |
| `organisation` | organisations, people, relationships, products, locations |
| `knowledge` | verified facts, evidence, sources, confidence, disclosure |
| `executive` | objectives, priorities, initiatives, decisions, risks, KPIs |
| `planning` | planning requests, plans, plan versions, steps, dependencies |
| `governance` | capability truth, policy decisions, approvals, authorisations |
| `integration` | connections, external accounts, inbound events, proposed actions |
| `documents` | document metadata, versions, chunks, embeddings, access policy |
| `audit` | audit events, state transitions, security events, model invocations |
| `system` | feature flags, runtime deployments, health snapshots |

## Table Summary

| table | purpose | keys and constraints | lifecycle | sensitivity | RLS intent |
| --- | --- | --- | --- | --- | --- |
| `identity.tenants` | canonical tenant boundary | `tenant_id` PK, unique slug | active, suspended, archived | high | tenant members only; support break-glass audited |
| `identity.users` | Hermes user profile linked to Auth | `user_id` PK, `auth_user_id` unique | active, disabled | high | self plus tenant admins |
| `identity.tenant_memberships` | user-tenant membership | PK `membership_id`, unique tenant/user | invited, active, revoked | high | same tenant, role limited |
| `identity.roles` | reusable roles | PK `role_id`, unique tenant/name | active, deprecated | medium | tenant admins read/write |
| `identity.permissions` | permission grants | PK `permission_id`, unique role/capability/action | active | medium | tenant admins read/write |
| `organisation.organisations` | canonical orgs | PK `organisation_id`, unique tenant/normalized_name | proposed, active, merged, archived | medium/high | tenant and sensitivity filtered |
| `organisation.legal_entities` | legal operating entities | FK organisation | active, inactive | high | restricted legal role required |
| `organisation.brands` | brands and programmes | FK organisation, unique tenant/name | active, archived | medium | brand-scoped membership |
| `organisation.people` | people and stakeholders | unique tenant/normalized identity when known | proposed, active, inactive | high | sensitivity and relationship scope |
| `organisation.business_roles` | person's role in context | FK person/org | current, historical | medium/high | tenant and role filtered |
| `organisation.relationships` | person/org/entity relationships | FK source/target, type, effective dates | current, ended | medium/high | both sides allowed |
| `organisation.locations` | physical/operating locations | FK organisation/brand | active, closed | medium | tenant/brand filtered |
| `organisation.programmes` | programmes and offerings | FK organisation/brand | planned, active, paused, ended | medium | tenant/brand filtered |
| `organisation.products` | products/services | FK organisation/brand | active, deprecated | medium | tenant/brand filtered |
| `organisation.customer_segments` | market segments | FK organisation | active | medium | tenant filtered |
| `organisation.partners` | partner organisations | FK organisation/person optional | active, dormant | medium/high | tenant and sensitivity filtered |
| `knowledge.business_facts` | current verified facts | PK fact_id, unique tenant/entity/fact_type/current | proposed, verified, disputed, superseded | variable | disclosure policy plus tenant |
| `knowledge.fact_versions` | immutable fact history | FK fact_id, version unique | immutable | variable | follows parent fact |
| `knowledge.evidence` | evidence metadata and references | PK evidence_id, checksum/source refs | active, redacted, deleted | variable | policy and document access |
| `knowledge.sources` | source system/message/file refs | unique tenant/source/idempotency | active, redacted | high | source-specific policy |
| `knowledge.fact_conflicts` | conflicting fact tracking | FK fact ids | open, resolved | high | reviewers only when sensitive |
| `knowledge.disclosure_policies` | allowed disclosure by channel/role | unique tenant/policy_key | active, retired | high | governance admins |
| `knowledge.knowledge_reviews` | review decisions | FK fact/evidence/reviewer | pending, accepted, rejected | high | reviewers/admins |
| `executive.objectives` | durable goals | unique tenant/objective/version | proposed, active, achieved, retired | medium/high | tenant plus role |
| `executive.priorities` | current priorities | FK objective/initiative | active, paused, done | medium | tenant plus role |
| `executive.initiatives` | strategic initiatives | FK org/objective | proposed, active, paused, closed | medium/high | tenant/brand |
| `executive.projects` | operational projects | FK initiative | planned, active, blocked, closed | medium | tenant/brand |
| `executive.commitments` | commitments and promises | FK person/org/evidence | open, done, overdue, cancelled | high | owner/tenant, sensitive filtered |
| `executive.decisions` | decisions and rationale | FK evidence, actor | proposed, made, reversed | high | decision participants/admins |
| `executive.risks` | risk register | FK entity/evidence | open, mitigated, accepted, closed | high | sensitivity filtered |
| `executive.kpis` | metric definitions | unique tenant/name | active, retired | medium/high | tenant/finance role as needed |
| `executive.metric_observations` | metric values | FK kpi, observed_at index | immutable/corrected | high | metric policy |
| `executive.executive_state_snapshots` | scheduled read-model snapshots | PK snapshot_id, tenant/date | immutable/redacted | high | tenant/role, no raw prompt |
| `planning.planning_requests` | incoming planning needs | idempotency key | received, analysed, closed | high | actor/tenant |
| `planning.plans` | plan aggregate | FK request/objective | draft, proposed, approved, archived | high | tenant/approver |
| `planning.plan_versions` | immutable versions | unique plan/version | immutable | high | follows plan |
| `planning.plan_steps` | steps/work items | FK plan_version | proposed, accepted, superseded | high | follows plan |
| `planning.dependencies` | plan dependencies | FK plan/step | open, resolved | medium/high | follows plan |
| `planning.assumptions` | assumptions | FK plan_version/evidence | active, invalidated | medium | follows plan |
| `planning.risks` | plan risks | FK plan_version | open, mitigated | high | follows plan |
| `planning.success_measures` | success criteria | FK plan_version | proposed, accepted | medium | follows plan |
| `planning.approval_requirements` | required approvals | FK plan/policy | pending, satisfied, expired | high | approvers/admins |
| `governance.capability_truth` | capability state | unique tenant/capability/channel | unavailable, read_only, proposal_only, enabled | high | tenant/admin, read safe summary |
| `governance.policy_decisions` | deterministic policy outcomes | idempotency key, FK actor | immutable | high | admin/audit |
| `governance.improvement_proposals` | proposal-only self-improvement | unique tenant/proposal/digest | proposed, reviewed, accepted, rejected | medium/high | operator/admin |
| `governance.approval_records` | human decisions | unique request/actor/version | immutable/revoked | high | actor/approver/admin |
| `governance.authorisations` | future authorisation grants | FK approval/policy | pending, active, expired, revoked | very high | tightly restricted |
| `integration.connections` | connector install state | unique tenant/provider/account | configured, unavailable, revoked | secret metadata high | no broad service-role reads |
| `integration.external_accounts` | external account identity | FK connection | active, disabled | high | tenant/admin |
| `integration.inbound_events` | idempotent external events | unique provider/event_id | received, processed, rejected | high | connector service plus audit |
| `integration.proposed_external_actions` | declarative actions | idempotency key, FK plan/actor | proposed, approved_not_executable, blocked, executed_future | very high | no execution from read path |
| `integration.external_action_receipts` | future execution receipts | FK action, external id unique | immutable | very high | restricted, never fabricated |
| `integration.synchronisation_cursors` | connector cursor state | unique connection/cursor_name | active, reset | high | connector service only |
| `documents.documents` | document aggregate | PK document_id, checksum indexes | active, archived, deleted, legal_hold | high | document policy |
| `documents.document_versions` | version metadata | unique document/version | immutable/redacted | high | follows document |
| `documents.document_chunks` | extracted text chunks | FK version, chunk index | active, redacted | high | follows document |
| `documents.embeddings` | vector metadata and vector | FK chunk/fact, model/version | active, stale, deleted | high | tenant/sensitivity filter before vector search |
| `documents.document_access_policies` | explicit document access | FK document/role/user | active, revoked | high | policy admins |
| `audit.audit_events` | append audit journal | PK event_id, idempotency/correlation index | immutable/redacted | variable | tenant/auditor; minimal payload |
| `audit.state_transitions` | lifecycle transitions | FK aggregate | immutable | high | auditors/admins |
| `audit.security_events` | auth/RLS/policy violations | FK actor/tenant | immutable | very high | security/admin only |
| `audit.disclosure_decisions` | disclosure allow/block records | idempotency key | immutable | high | auditors/admins |
| `audit.model_invocations` | safe model metadata | provider/model/digests, no raw prompt | immutable/redacted | high | operator/auditor |
| `system.feature_flags` | feature state metadata | unique tenant/flag | active, retired | medium/high | operators/admins |
| `system.deployments` | deployed SHA/status | service/sha/timestamp unique | immutable | medium | operators |
| `system.health_snapshots` | health readouts | service/time index | immutable/retained | medium | operators |

## Common Columns

Most tenant-scoped tables should include:

- `tenant_id uuid not null`;
- `owner_user_id uuid` where ownership matters;
- `sensitivity text not null default 'internal'`;
- `disclosure_policy_id uuid`;
- `source_evidence_id uuid`;
- `confidence numeric`;
- `status text`;
- `effective_from timestamptz`;
- `effective_to timestamptz`;
- `created_at timestamptz not null default now()`;
- `updated_at timestamptz not null default now()`;
- `created_by uuid`;
- `updated_by uuid`;
- `idempotency_key text` for ingestion/action paths.

## Index Principles

- Every table with `tenant_id` gets a leading `tenant_id` index.
- Current-state tables get `(tenant_id, status, updated_at desc)`.
- Event and audit tables get `(tenant_id, occurred_at desc)`,
  `(correlation_id)`, and `(causation_id)`.
- External events/actions get unique idempotency indexes.
- Vector tables must index tenant/sensitivity metadata as well as the vector.
- Sensitive legal/financial records should favour explicit policy joins over
  broad JSONB filters.

## RLS Principles

Each table should state whether access is tenant, owner, role, brand, document,
or operator scoped. Service-role operations should be wrapped by narrow database
functions where broad table access would create a confused-deputy risk.
