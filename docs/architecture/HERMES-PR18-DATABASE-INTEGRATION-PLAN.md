# Hermes PR #18 Database Integration Plan

Status: compatibility plan only. PR #18 remains unmerged.

## Objective

When PR #18 is rebased, it must consume Slice 1 database-backed governance
state rather than establishing local or YAML-backed runtime authority.

## Required Changes

`gateway/capability_truth.py`:

- keep deterministic code safety ceilings;
- delegate tenant/channel/user/environment overlays to
  `gateway.edp_governance.CapabilityTruthEvaluator`;
- label CLI/status values as `code_ceiling`, `database_overlay`,
  `effective_state`, `proposal_only` or `unavailable`;
- fail closed on unknown capability keys, database errors or conflicts.

`agent/background_review.py`:

- create durable records through
  `public.ovos_edp_create_improvement_proposal(jsonb)`;
- treat persistence failure as surfaced degraded state;
- never apply proposals directly.

`gateway/business_knowledge.py`:

- remain explicitly non-authoritative until the Business Knowledge PostgreSQL
  milestone;
- treat YAML and in-memory records as seed/import/test material only;
- do not claim production business truth from local files.

`hermes_cli/governance.py`:

- reuse the Slice 1 governance CLI shape;
- show the source of every value;
- avoid broad service-role use unless explicitly configured for bounded
  diagnostics;
- do not add mutation commands.

Bootstrap YAML:

- may seed proposed facts or policy candidates;
- must not become live authoritative Capability Truth, Business Knowledge or
  Improvement Proposal state.

## Non-Execution Requirement

No PR #18 component may enable connectors, approvals, external execution,
outbound writes, MCP execution or self-modification. The execution boundary
remains `not_executed`.
