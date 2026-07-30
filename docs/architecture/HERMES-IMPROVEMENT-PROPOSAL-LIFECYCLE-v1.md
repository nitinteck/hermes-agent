# Hermes Improvement Proposal Lifecycle v1

Status: Foundation Slice 1 implementation.

## Purpose

Improvement Proposals let Hermes record safe, reviewable ideas without
performing self-modification. They are durable governance records, not an
execution mechanism.

## Table

`ovos.edp_improvement_proposals` stores:

- `proposal_id`
- `tenant_id`
- `proposal_type`
- `title`
- `safe_summary`
- `rationale`
- `affected_component`
- `proposed_change_ref`
- `risk_classification`
- `proposer_actor_type`
- `proposer_user_id`
- `status`
- reviewer and timestamp fields
- `correlation_id`
- `source_event_reference`
- bounded `metadata`

The table must not contain raw prompts, secrets, credentials, unrestricted code
payloads, private message dumps or hidden mutable state.

## Statuses

- `proposed`
- `under_review`
- `approved`
- `rejected`
- `superseded`
- `applied`
- `failed`
- `withdrawn`

Transitions are enforced by a bounded RPC. Terminal statuses cannot transition.

## Non-Execution Guarantees

Creating or approving a proposal does not:

- modify skills;
- rewrite prompts;
- change routing;
- change profiles;
- change capabilities;
- alter feature flags;
- deploy code;
- trigger adapters;
- execute external actions.

RPC receipts include `direct_mutation_performed=false` and
`execution_status=not_executed`.
