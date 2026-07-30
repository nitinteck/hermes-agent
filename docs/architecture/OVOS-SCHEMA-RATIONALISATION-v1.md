# OVOS Schema Rationalisation v1

Status: read-only architecture audit. No PR was merged, no deployment was made,
no migration was applied, and no production data was modified.

## Source Evidence

- Local Supabase development catalog queried read-only on port `55422`.
- `ovos-core` migration files inspected through `20260729130000`.
- `hermes-agent` and `ovos-core` repositories scanned for table references.
- PR #18 and PR #19 were verified open and unmerged during the audit.
- VPS was inspected read-only for deployed SHAs and process posture.

Row counts are local development counts only. They are included to support
structural analysis and do not expose row contents.

## Totals

| Metric | Count |
| --- | ---: |
| Non-system schemas | 9 |
| Non-system tables | 150 |
| `ovos` application tables | 102 |
| Functions/RPCs in local catalog, all non-system schemas | 162 |
| OVOS application functions/RPCs (`ovos.*` plus `public.ovos_*`) | 48 |
| Tables with trigger event rows | 35 |
| Actual non-internal trigger objects, all non-system schemas | 40 |
| Actual non-internal OVOS trigger objects | 35 |
| `information_schema.triggers` event rows used in table catalog | 57 |
| RLS-enabled tables | 129 |
| RLS policies attached to inspected tables | 88 |

## Schemas

| Schema | Tables |
| --- | --- |
| _realtime | 3 |
| auth | 21 |
| net | 2 |
| ovos | 102 |
| realtime | 8 |
| storage | 10 |
| supabase_functions | 2 |
| supabase_migrations | 1 |
| vault | 1 |

## Functional Classifications

| Domain | Tables |
| --- | --- |
| Audit | 7 |
| Core Identity | 21 |
| Executive | 65 |
| Integration | 12 |
| Knowledge | 15 |
| Operational | 2 |
| Organisation | 7 |
| System | 21 |

## Architectural Ownership

| Architectural Ownership | Tables |
| --- | --- |
| Executive Data Platform | 87 |
| Infrastructure | 48 |
| OVOS Core | 15 |

## Active Versus Legacy

| State | Tables |
| --- | --- |
| Active platform | 48 |
| Active referenced | 102 |

No table is recommended for immediate drop. Several EDE tables have low current
runtime evidence but are recent domain scaffolding, not proven legacy. Treat
unreferenced EDE tables as active schema pending implementation evidence.

## Rationalisation Matrix

| Table | Purpose | Current Owner | Architectural Ownership | Hermes Uses? | Keep | Extend | Replace | Deprecate | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _realtime.extensions | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | Direct | Yes | No | No | No | High |
| _realtime.schema_migrations | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| _realtime.tenants | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | Direct | Yes | No | No | No | High |
| auth.audit_log_entries | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.custom_oauth_providers | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.flow_state | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | Direct | Yes | No | No | No | High |
| auth.identities | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | Direct | Yes | No | No | No | High |
| auth.instances | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | Direct | Yes | No | No | No | High |
| auth.mfa_amr_claims | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.mfa_challenges | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.mfa_factors | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.oauth_authorizations | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.oauth_client_states | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.oauth_clients | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.oauth_consents | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.one_time_tokens | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.refresh_tokens | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | Direct | Yes | No | No | No | High |
| auth.saml_providers | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.saml_relay_states | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.schema_migrations | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.sessions | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | Direct | Yes | No | No | No | High |
| auth.sso_domains | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.sso_providers | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | No evidence | Yes | No | No | No | High |
| auth.users | Supabase Auth platform table for identity, sessions, tokens, MFA, OAuth, SSO, or audit. | Supabase Auth | Infrastructure | Direct | Yes | No | No | No | High |
| net._http_response | Supabase network extension queue/response table. | Supabase pg_net | Infrastructure | Direct | Yes | No | No | No | High |
| net.http_request_queue | Supabase network extension queue/response table. | Supabase pg_net | Infrastructure | No evidence | Yes | No | No | No | High |
| ovos.attachments | Attachment metadata and private object-storage references. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | High |
| ovos.conversation_messages | Message provenance and content metadata. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | High |
| ovos.conversation_participants | Participants linked to stored conversations. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.conversation_signals | Detected decisions, commitments, dates, and follow-up signals. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.conversation_summaries | Generated bounded conversation summaries. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.conversations | Conversation thread provenance. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | High |
| ovos.ede_action_parameter_schemas | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_action_proposal_sets | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_action_proposals | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_approval_decisions | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_approval_policies | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_approval_requests | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_brief_items | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_capabilities | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_capability_gaps | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_capacity_records | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_clarifications | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_competencies | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_context_references | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_evidence_graph_edges | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_evidence_graph_nodes | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_evidence_links | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_attempts | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_authorisations | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_eligibility_assessments | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_handoff_drafts | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_outcomes | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_policies | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_policy_decisions | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_requests | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_risk_assessments | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_safety_receipts | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_execution_simulations | EDE execution safety-kernel record; declarative and non-executing in current milestones. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_executive_plans | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_feedback | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_intelligence_briefs | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_interpretation_runs | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_kernel_control_states | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_lesson_candidates | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_lesson_reviews | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_object_versions | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_objects | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_edge_versions | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_edges | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_evidence_links | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_node_versions | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_nodes | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_projection_runs | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_okg_traversal_audit | EDE organisational knowledge graph projection/version/audit record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_organisational_dna_candidates | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_adoptions | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_candidates | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_change_proposals | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_drift_findings | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_execution_outcomes | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_experiments | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_signals | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_steps | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_variations | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_pattern_versions | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_patterns | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_plan_change_requests | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_controls | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_dependencies | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_evidence_links | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_objectives | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_outcomes | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_phases | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_readiness_assessments | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_reviews | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_risks | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_steps | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_versions | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_plan_workstreams | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_planning_action_proposals | EDE planning and approval lifecycle record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.ede_playbook_patterns | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_playbook_steps | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_playbook_versions | EDE pattern evolution, playbook, lesson, or organisational DNA record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_reasoning_feedback | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_reasoning_passes | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_reasoning_runs | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_recommendations | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_role_assignments | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_role_definitions | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_target_system_definitions | EDE foundation object, interpretation, context, evidence, capability, role, or feedback record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.ede_watch_item_proposals | EDE executive reasoning/intelligence output record. | OVOS EDE | Executive Data Platform | Indirect via ovos-core | Yes | No | No | No | High |
| ovos.evidence_items | Evidence item metadata. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.evidence_source_links | Join table linking evidence to sources. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.executive_daily_briefs | Generated daily executive brief records. | Hermes/OVOS executive context | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.executive_event_journal | Hermes executive event journal. | Hermes/OVOS executive context | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | High |
| ovos.executive_identities | Executive user identity/profile context. | Hermes/OVOS executive context | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | Medium |
| ovos.knowledge_memories | Versioned memory records grounded in knowledge evidence. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.knowledge_objects | Captured knowledge object extracted from source material. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | High |
| ovos.networking_observations | Networking and relationship memory observations. | OVOS Core | OVOS Core | Indirect via ovos-core | Yes | No | No | No | Medium |
| ovos.organisation_contexts | Organisation profile and operating context. | OVOS Core | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | Medium |
| ovos.processing_events | Processing/audit events for capture and extraction. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | Medium |
| ovos.relationships | Generic relationship edges between captured entities. | OVOS Core | OVOS Core | Direct | Yes | Yes | No | No | Medium |
| ovos.responsibility_assignments | Responsibility mappings for people/teams. | OVOS Core | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | Medium |
| ovos.source_records | Source-system provenance for captured knowledge. | OVOS Core | OVOS Core | Direct | Yes | No | No | No | High |
| ovos.team_capabilities | Capabilities associated with known team members. | OVOS Core | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | Medium |
| ovos.team_members | Known team members and stakeholder people. | OVOS Core | Executive Data Platform | Indirect via ovos-core | Yes | Yes | No | No | Medium |
| ovos.workflow_feedback | Feedback records about workflow outcomes. | OVOS Core | OVOS Core | Indirect via ovos-core | Yes | No | No | No | Medium |
| realtime.messages | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | Direct | Yes | No | No | No | High |
| realtime.messages_2026_07_28 | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| realtime.messages_2026_07_29 | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| realtime.messages_2026_07_30 | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| realtime.messages_2026_07_31 | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| realtime.messages_2026_08_01 | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| realtime.schema_migrations | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | No evidence | Yes | No | No | No | High |
| realtime.subscription | Supabase Realtime platform table or partition. | Supabase Realtime | Infrastructure | Direct | Yes | No | No | No | High |
| storage.buckets | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | Direct | Yes | No | No | No | High |
| storage.buckets_analytics | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| storage.buckets_vectors | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| storage.iceberg_namespaces | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| storage.iceberg_tables | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| storage.migrations | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | Direct | Yes | No | No | No | High |
| storage.objects | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | Direct | Yes | No | No | No | High |
| storage.s3_multipart_uploads | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| storage.s3_multipart_uploads_parts | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| storage.vector_indexes | Supabase Storage platform table for buckets, objects, analytics, S3 multipart, or vector storage metadata. | Supabase Storage | Infrastructure | No evidence | Yes | No | No | No | High |
| supabase_functions.hooks | Supabase Edge Functions platform metadata. | Supabase Edge Functions | Infrastructure | Direct | Yes | No | No | No | High |
| supabase_functions.migrations | Supabase Edge Functions platform metadata. | Supabase Edge Functions | Infrastructure | Direct | Yes | No | No | No | High |
| supabase_migrations.schema_migrations | Supabase platform migration or secrets metadata. | Supabase migrations | Infrastructure | No evidence | Yes | No | No | No | High |
| vault.secrets | Supabase platform migration or secrets metadata. | Supabase Vault | Infrastructure | Direct | Yes | No | No | No | High |

## Highest Architectural Risks

1. Supabase Auth and Storage already provide identity and document primitives;
   Hermes should reuse them rather than introduce parallel user, token, bucket,
   or object stores.
2. The `ovos` schema already contains EDE planning, approval, execution safety,
   daily brief, event journal, knowledge, evidence, conversation, and executive
   context tables. New EDP work should extend these first.
3. Local Hermes `state.db` remains a separate source of truth for sessions and
   transcripts. That may be acceptable during runtime, but executive summaries,
   evidence references, and durable trace records should move into OVOS/Supabase
   read models.
4. PR #18's Business Knowledge Registry, Capability Truth, and improvement
   proposal concepts should map onto existing or extended OVOS tables before
   they become production authority.
5. The VPS `ovos-core` checkout was observed ahead of `origin/main`; reconcile
   source parity before any schema-changing milestone.

## Conclusion

Hermes should build on top of OVOS. The first EDP implementation should reuse
Supabase Auth, Supabase Storage, OVOS knowledge/evidence/conversation tables,
existing EDE planning/approval/safety tables, and the executive event journal.
Only capability truth, improvement proposals, canonical tenant membership
bridging, document chunks/embeddings, and derived executive state snapshots need
new or substantially extended structures.
