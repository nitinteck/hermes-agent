# Hermes PR #18 EDP Alignment Review v1

Status: architecture review only. PR #18 was not merged or modified by this
audit.

PR reviewed: `https://github.com/nitinteck/hermes-agent/pull/18`
Head inspected: `78a8e7913ef831801b8dad3634dee1d14b9ffee7`

## Component Classification

| component | classification | rationale |
| --- | --- | --- |
| `gateway/governance.py` | merge now but migrate persistence later | The disclosure and governance controls are useful, but decisions that matter operationally should become auditable PostgreSQL records. |
| `gateway/capability_truth.py` | merge now but migrate persistence later | Code-defined deny/default capability truth is a safe baseline. Tenant/channel capability overlays and connector state need PostgreSQL. |
| `agent/background_review.py` | merge largely unchanged | Proposal-only self-improvement is aligned with safety, provided proposals cannot be applied without review. |
| `gateway/executive_planning.py` | merge now but migrate persistence later | Planning safety and context improvements are useful, but durable planning state belongs in EDE/PostgreSQL. |
| `gateway/business_knowledge.py` | revise before merge | The registry must be explicitly documented and coded as an application abstraction, not an in-memory source of truth. |
| `hermes_cli/governance.py` | merge now but migrate persistence later | Operator visibility is useful. Future commands should read auditable DB records and avoid broad service-role exposure. |
| bootstrap YAML | merge now but migrate persistence later | YAML may seed/import proposed facts and policies. It must not become live authoritative business state. |
| modular conversational test packs | merge largely unchanged | Tests are valuable and do not create durable state. |

## Decisions

1. Capability Truth should be hybrid-owned:
   - code owns immutable deny defaults and non-execution guarantees;
   - PostgreSQL owns tenant/channel capability state, connection availability,
     disclosure records, and authorised overlays.
2. Improvement Proposals do not require immediate PostgreSQL persistence if they
   remain proposal-only and non-applied, but they should be persisted before any
   operator workflow depends on review history.
3. Business Knowledge Registry should remain an application abstraction backed
   by PostgreSQL. The in-memory implementation should be test/dev only.
4. YAML should be limited to seed/import data, fixtures, and test packs.
5. PR #18 risks creating a competing source of truth only if the in-memory
   Business Knowledge Registry or YAML bootstrap records are treated as
   production authority.

## Required PR #18 Revisions Before Merge

- Mark `gateway/business_knowledge.py` in code comments or docs as non-
  authoritative until backed by PostgreSQL.
- Ensure any runtime use of the in-memory business registry is test/dev only or
  explicitly read-only seed context.
- Add a short note that bootstrap YAML is import seed material, not production
  truth.
- Ensure governance CLI output says when data is code-derived or proposal-only
  rather than database authoritative.

## Merge Recommendation

Do not merge PR #18 until the minimal clarifications above are made. After
those are added, PR #18 can be merged as governance hardening, not as the
Executive Data Platform foundation.
