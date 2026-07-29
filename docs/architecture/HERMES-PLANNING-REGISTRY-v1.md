# Hermes Planning Registry v1

Last updated: 2026-07-29

The Planning Registry is separate from Context, Intelligence, Integration,
Adapter and Skill registries.

It records:

- strategy ID
- version
- description
- supported plan types
- deterministic status
- enabled state
- lifecycle state
- evidence requirements
- execution support
- external-call support
- health
- risk

Current strategies:

| Strategy | Purpose | External Calls |
| --- | --- | --- |
| `milestone_plan` | Strategic milestone and organisational planning | false |
| `implementation_plan` | Technical/process rollout planning | false |
| `decision_plan` | Option comparison and recommendation conditions | false |
| `review_plan` | Evidence-first review sequence | false |

Registry output is operator-safe and exposed through:

```bash
hermes planning strategies
hermes planning status
```

The registry does not execute strategies through tools or adapters. It only
describes deterministic planning templates used by `ExecutivePlanningEngine`.
