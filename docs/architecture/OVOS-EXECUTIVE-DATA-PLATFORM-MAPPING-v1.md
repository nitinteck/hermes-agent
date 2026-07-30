# OVOS Executive Data Platform Mapping v1

Status: maps the PR #19 EDP model onto existing OVOS and Supabase objects.

## Entity Mapping

| Proposed Entity | Existing Table? | Extend Existing? | New Table Required? | Notes |
| --- | --- | --- | --- | --- |
| tenants | auth has users but no OVOS tenant table | Extend with identity.tenants or reuse existing tenant_id columns plus membership bridge | Yes for canonical tenant table | Existing tables use tenant_id without lifecycle table. |
| users | auth.users | Extend via Hermes user profile table or mapping | Maybe | Reuse Supabase Auth as identity root. |
| memberships | none explicit | New/extend identity layer | Yes | Needed for RLS and dashboard/operator roles. |
| organisations | ovos.organisation_contexts | Extend existing | No immediate new table if extended | Turn context records into canonical org abstraction or add narrow canonical org table later. |
| brands | brand_id columns and org context arrays | Extend existing EDE/entity model | Maybe | Brand ids exist as fields, canonical brand lifecycle is missing. |
| people | team_members, executive_identities, conversation_participants | Extend existing | No immediate new table | Consolidate person semantics before creating new table. |
| relationships | ovos.relationships, ede_okg_edges | Extend/wrap existing | No | Avoid new graph table until edge semantics are rationalised. |
| objectives | ede_plan_objectives, ede_objects | Extend existing | No | Use EDE planning/object tables first. |
| projects | ede_executive_plans, ede_plan_workstreams/steps | Extend existing | Maybe later | Project aggregate may be derived from plans/workstreams initially. |
| decisions | ede_reasoning_runs, recommendations, approval decisions, event journal | Extend existing | No immediate new table | Decision read model can derive from EDE plus approvals. |
| risks | ede_plan_risks, execution risk assessments, event journal | Extend existing | No | Risk register can wrap existing risk tables. |
| commitments | conversation_signals, event journal | Extend existing | Maybe | Current commitment extraction exists but canonical commitment lifecycle is thin. |
| plans | ede_executive_plans, plan_versions, steps, dependencies | Reuse existing | No | Do not duplicate planning schema. |
| approvals | ede_approval_* | Reuse existing | No | Approval lifecycle already exists. |
| execution requests | ede_execution_* | Reuse existing | No | Safety kernel tables already exist and remain non-executing. |
| capability truth | ede_capabilities plus PR #18 code registry | Extend existing or add governance overlay | Maybe | Need tenant/channel capability state and connection truth. |
| improvement proposals | none durable | No existing fit | Yes | Proposal-only self-improvement needs auditable records. |
| audit events | executive_event_journal, EDE journals, auth audit_log_entries | Extend/wrap existing | No immediate new table | Use executive_event_journal plus specific audit tables before adding generic audit schema. |
| business facts | knowledge_objects, knowledge_memories, ede_objects | Reuse and extend | No immediate new table | Create abstraction over existing fact/object structures. |
| documents | attachments, evidence_items, storage.objects | Reuse existing | No | Document aggregate can wrap storage/evidence/attachments. |
| document chunks | none explicit | New table required | Yes | Needed for hybrid retrieval. |
| embeddings | storage vector metadata only, no app table | New table required | Yes | Need governed pgvector metadata. |
| evidence | evidence_items, evidence_source_links, source_records | Reuse existing | No | Strong existing base. |
| state snapshots | executive_daily_briefs, event journal | Extend existing | Maybe | Executive state snapshots can extend current daily brief/event model. |

## Genuine Gaps

| Gap | Existing nearest fit | Recommended action |
| --- | --- | --- |
| Canonical tenant lifecycle and membership bridge | tenant_id/owner_user_id columns, Supabase Auth | Add identity bridge tables or extend OVOS identity foundation. |
| Tenant/channel Capability Truth overlay | ede_capabilities, PR #18 code registry | Extend with DB-backed capability truth records. |
| Improvement proposals | PR #18 in-memory proposal-only objects | Add governance.improvement_proposals or equivalent OVOS table. |
| Document chunks | attachments, evidence_items, storage.objects | Add chunk table linked to document/evidence metadata. |
| Governed embeddings | storage vector config, no app table | Add pgvector/embedding metadata table with RLS. |
| Derived Executive State snapshot/read model | daily briefs, event journal, EDE planning/reasoning | Create read model/view/snapshot over existing tables. |

## Recommended New Tables

Only these should be considered new table candidates in the next implementation
planning pass:

1. Tenant membership/profile bridge if existing Auth plus `tenant_id` columns are
   insufficient.
2. Capability truth overlay if `ede_capabilities` cannot carry tenant/channel
   availability and connection truth cleanly.
3. Improvement proposals.
4. Document chunks.
5. Embedding metadata/vector rows.
6. Executive state snapshots/read-model materialisation, if views alone are not
   enough.

Everything else should first reuse, extend, or wrap existing OVOS/Supabase
objects.
