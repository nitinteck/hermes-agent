# OVOS Duplication Analysis v1

Status: read-only architecture analysis.

| Concept | Existing overlap | Risk | Recommendation |
| --- | --- | --- | --- |
| Identity/users | Supabase Auth users/sessions/tokens and tenant_id/owner_user_id columns in ovos | Hermes could create parallel users/memberships instead of Auth-backed identity. | Reuse Auth; add only Hermes tenant membership/profile bridge. |
| Business facts | knowledge_objects, knowledge_memories, ede_objects, organisation_contexts, PR #18 registry | Multiple fact stores with different confidence/provenance semantics. | Wrap existing OVOS knowledge/EDE objects before adding new facts table. |
| Relationships/graph | ovos.relationships, ede_okg_edges, ede_evidence_graph_edges | Entity relationships and evidence graph edges diverge. | Define edge taxonomy and read abstraction. |
| Plans/projects | ede_executive_plans, plan versions/steps/workstreams, PR #18 planning objects | Hermes planning could duplicate EDE planning schema. | Use EDE planning tables; PR #18 objects remain runtime/view abstractions. |
| Approvals/execution | ede_approval_* and ede_execution_* safety tables | New approval/execution tables could bypass safety kernel lineage. | Reuse and extend EDE tables; approval never executes. |
| Event/audit traces | executive_event_journal, EDE journal tables, local JSONL traces, logs | Auditable truth split between host files and Supabase. | Keep local traces as diagnostics; persist durable audit in OVOS. |
| Documents/evidence | storage.objects, attachments, evidence_items, source_records | A new document store could detach files from provenance and RLS. | Wrap Storage + evidence tables; add chunks/embeddings only. |
| Capability truth | ede_capabilities, PR #18 deterministic registry, config/env connector state | Capability honesty may diverge from installed/authorised connectors. | Hybrid: code deny defaults plus DB tenant/channel capability state. |

## Where Hermes Is Most Likely To Reinvent Existing OVOS Structures

- Planning: use `ovos.ede_executive_plans` and related plan tables instead of
  introducing a Hermes-only project/plan store.
- Approvals: use `ovos.ede_approval_requests` and `ovos.ede_approval_decisions`.
- Execution safety: use `ovos.ede_execution_*` rather than any runtime approval
  shortcut.
- Evidence: use `ovos.evidence_items`, `ovos.evidence_source_links`, and
  `ovos.source_records`.
- Documents: wrap `storage.objects`, `ovos.attachments`, and evidence metadata.
- Executive journal: extend `ovos.executive_event_journal` instead of relying on
  local JSONL traces as durable audit.
