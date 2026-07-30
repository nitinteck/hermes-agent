# Hermes Event Model v1

Status: target model. No event table has been created by this document.

## Recommendation

Use conventional mutable canonical tables plus append-only audit events,
versioned records, and scheduled state snapshots. Do not adopt full event
sourcing for Hermes v1.

Rationale:

- Operators and product code need simple current-state queries.
- Evidence, approvals, plans, capability changes, and execution receipts need
  immutable history.
- Full event sourcing would add replay complexity before Hermes has stable
  domain boundaries.
- Selective event sourcing gives auditability without turning every read into a
  projection problem.

## Event Envelope

Every event should include:

| field | requirement |
| --- | --- |
| `event_id` | UUID primary key |
| `tenant_id` | required tenant boundary |
| `actor_type` | human, system, model, connector, operator |
| `actor_id` | safe identifier, nullable for unauthenticated rejected events |
| `aggregate_type` | stable domain aggregate name |
| `aggregate_id` | aggregate UUID or safe external reference |
| `event_type` | controlled event type |
| `schema_version` | integer version for payload parsing |
| `occurred_at` | source occurrence time |
| `recorded_at` | database insertion time |
| `correlation_id` | end-to-end request/turn correlation |
| `causation_id` | previous event/action that caused this event |
| `payload` | safe JSONB only |
| `payload_digest` | hash of redacted payload |
| `sensitivity` | public, internal, confidential, restricted, secret |
| `retention_policy` | retention class |

Payloads must not contain full private prompts, system prompts, secrets, OAuth
tokens, complete connector payloads, or hidden reasoning.

## Event Categories

| event_type | aggregate | safe payload examples |
| --- | --- | --- |
| `request_received` | conversation_turn | channel, message_digest, actor_ref |
| `context_retrieved` | context_snapshot | source counts, evidence ids, context_digest |
| `fact_proposed` | business_fact | fact_type, confidence, evidence_refs |
| `fact_verified` | business_fact | reviewer_ref, verification_method |
| `fact_superseded` | business_fact | previous_fact_id, reason_code |
| `conflict_detected` | fact_conflict | conflicting_fact_ids, confidence |
| `intelligence_generated` | intelligence_output | output_type, evidence_refs, digest |
| `reasoning_completed` | model_invocation | provider, model, latency, prompt_digest |
| `plan_proposed` | plan | plan_id, version, objective_refs |
| `plan_revised` | plan | from_version, to_version, reason |
| `approval_requested` | approval_request | required_role, expires_at |
| `approval_recorded` | approval_record | decision, actor_role, plan_version |
| `action_proposed` | proposed_external_action | target_system, action_kind, execution_status |
| `action_authorised` | authorisation | approval_refs, expiry |
| `action_executed` | external_action_receipt | receipt_id, target_system, external_ref |
| `execution_failed` | external_action_receipt | failure_class, retryable |
| `outcome_observed` | outcome | metric_ref, evidence_refs |
| `capability_changed` | capability_truth | old_state, new_state, reason |
| `connection_changed` | connection | provider, state, actor_ref |
| `disclosure_blocked` | disclosure_decision | policy_id, reason_code |
| `policy_violation` | security_event | policy_id, blocked_operation |
| `improvement_proposed` | improvement_proposal | target_area, proposal_digest |

## Idempotency

Inbound platform events, model turns, proposed actions, approvals, and
connector sync events must carry idempotency keys. Replays should return the
existing event or fail closed if the same key maps to a different digest.

## Retention

- Security and approval events: long retention, redaction only by controlled
  policy.
- Model invocation metadata: retain digests, latency, provider/model, outcome,
  and evidence references; expire raw debugging metadata quickly.
- Connector inbound events: retain minimal metadata and evidence references;
  raw payload only when required.
- Documents and embeddings: deletion must propagate to chunks, embeddings, and
  retrieval indexes while preserving legal audit tombstones.
