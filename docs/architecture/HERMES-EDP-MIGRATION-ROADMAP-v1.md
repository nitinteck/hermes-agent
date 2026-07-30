# Hermes EDP Migration Roadmap v1

Status: staged plan. No migration has been applied.

## Stage 0: Architecture Confirmation

- Prerequisites: backup posture confirmed, VPS source parity resolved, PR #18
  alignment reviewed.
- Schema changes: none.
- Application changes: none except documentation.
- Validation: migration inventory, RLS inventory, service/process inventory.
- Rollback: no runtime change.
- Test gates: docs review and metadata-only audit.

## Stage 1: Tenancy, Identity, RLS, Audit Foundation

- Schema: `identity.tenants`, `users`, `tenant_memberships`, roles,
  permissions, `audit.audit_events`.
- Application: map current default tenant/owner config to explicit records.
- Migration: create new schemas/tables; do not move business facts yet.
- Backfill: current configured tenant/owner only after backup.
- Rollback: additive schema rollback before data dependency.
- Gates: RLS tests, service-role RPC tests, cross-tenant negative tests.

## Stage 2: Capability Truth And Governance

- Schema: `governance.capability_truth`, `policy_decisions`,
  `improvement_proposals`.
- Application: PR #18 deterministic baseline reads DB overlays but fails closed.
- Dual-read: code baseline plus DB overlay.
- Rollback: disable DB overlay flag.
- Gates: capability honesty, no connector enablement, proposal-only tests.

## Stage 3: Business Knowledge Registry

- Schema: `knowledge.business_facts`, versions, evidence, disclosure policies,
  reviews.
- Application: Business Knowledge Registry becomes a repository-backed
  abstraction.
- Backfill: curated seed YAML imported as proposed facts, not authoritative
  truth.
- Gates: provenance, sensitivity, disclosure, conflict tests.

## Stage 4: Planning And Executive Records

- Schema: align existing EDE planning tables with canonical `planning` and
  `executive` read model.
- Application: planning objects persist to PostgreSQL; local plans become
  derived/test fixtures only.
- Gates: approval non-execution, stale version rejection, audit trails.

## Stage 5: Documents And Hybrid Retrieval

- Schema: documents, versions, chunks, embeddings, access policies.
- Application: ingestion queue and retrieval provider.
- Storage: private Supabase bucket first.
- Gates: deletion propagation, RLS vector filtering, citation tests.

## Stage 6: Executive State Read Model

- Schema: views/materialised views/snapshots.
- Application: Orchestrator uses read model as bounded source.
- Gates: freshness, evidence references, no duplicate source of truth.

## Stage 7: Integration Events And Connection State

- Schema: connections, external accounts, inbound events, sync cursors.
- Application: read-only connector event ingestion.
- Gates: connector read-only, no external writes, OAuth/audit tests.

## Stage 8: Approvals And Future Execution Lifecycle

- Schema: authorisations and external action receipts hardened around existing
  EDE safety kernel.
- Application: controlled execution boundary only after explicit milestone.
- Gates: approval does not execute, receipts cannot be fabricated, replay-safe
  idempotency, target-system allowlists.

## Deployment Order For Each Stage

1. Backup and restore-test checkpoint.
2. Apply additive schema to staging/local.
3. Run RLS and migration tests.
4. Deploy application reads behind disabled feature flag.
5. Backfill with validation.
6. Enable read paths.
7. Remove obsolete local authority only after parity reports pass.

No stage should require a big-bang rewrite.
