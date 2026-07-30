# OVOS Implementation Sequence v1

Status: recommended build order. No implementation performed.

| Stage | Action | Why first |
| --- | --- | --- |
| 1. Reuse identity | Anchor Hermes users to Supabase Auth and explicit tenant/member mapping. | RLS, dashboards, approvals, and disclosure all depend on actor/tenant truth. |
| 2. Extend organisation | Wrap organisation_contexts, team_members, relationships, and executive_identities. | Personalisation and executive context need governed org/person facts. |
| 3. Capability Truth | Extend ede_capabilities or add DB overlay for tenant/channel capability state. | Prevents connector and execution claims from drifting from reality. |
| 4. Improvement Proposals | Persist proposal-only self-improvement records. | Allows PR #18 governance work to become auditable without self-application. |
| 5. Business Knowledge | Create repository abstraction over knowledge_objects, memories, evidence, and EDE objects. | Avoids duplicate business fact store. |
| 6. Planning | Use EDE planning tables as canonical plans/projects/workstreams. | Planning already exists; Hermes should not reinvent it. |
| 7. Executive State | Build derived read model over objectives, plans, decisions, risks, commitments, briefs, and journal. | Executive State should emerge from existing state after core domains are stable. |
| 8. Approvals | Expose EDE approval lifecycle through safe UX/CLI abstractions. | Approvals need identity, planning, and audit already in place. |
| 9. Execution | Only after explicit future milestone, use EDE execution safety and receipts. | Execution is highest risk and must stay disabled until safety/approval foundations are proven. |
