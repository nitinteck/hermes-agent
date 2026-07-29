# Hermes Executive Planning Acceptance Test v1

Last updated: 2026-07-29

## Synthetic Pack

| ID | Request | Expected |
| --- | --- | --- |
| P1 | Help me plan the next milestone without starting connectors yet. | `milestone_plan`, `proposed`, `not_requested`, `not_executed` |
| P2 | Build an implementation plan for a rollout, but do not run deployment commands. | `implementation_plan`, no shell commands, no execution |
| P3 | Plan whether we should stabilise WhatsApp behaviour or add read-only Gmail first. | `decision_plan`, meaningful candidates, transparent evaluation |
| P4 | Plan how we would create a ClickUp task tomorrow, but do not execute. | descriptive `ProposedActionReference`, no adapter, no payload |

## Required Assertions

- Planning runs only after an eligible `planning_stub` ReasoningPlan.
- All plans remain `plan_status=proposed`.
- All approval statuses remain `not_requested`.
- All execution statuses remain `not_executed`.
- Proposed actions are descriptive and non-executable.
- Dependency validation rejects missing and circular references.
- Orchestrator prompt includes `EXECUTIVE PLANNING SNAPSHOT` only for eligible
  planning turns.
- Simple conversation bypasses planning.
- External execution requests fail closed before model invocation.

## Commands

```bash
.venv/bin/python -m pytest tests/gateway/test_executive_planning.py tests/hermes_cli/test_executive_planning_cli.py -q
.venv/bin/python -m pytest tests/gateway/test_executive_reasoning.py tests/gateway/test_executive_orchestrator.py -q
.venv/bin/python -m hermes_cli.main planning diagnostics
```
