# Hermes Governance Hardening Operations v1

Last updated: 2026-07-30

## Operator Commands

```bash
hermes governance status
hermes governance diagnostics
hermes ip-guard status
hermes capability-truth status
hermes improvement-proposals status
hermes business-context status
hermes business-context diagnostics
hermes business-context conflicts
hermes test-packs list
hermes executive-orchestrator status
hermes reasoning status
hermes planning status
```

Commands are operator-safe: they return booleans, counts, status names and safe
digests only. They do not print prompts, secrets, private business context,
restricted knowledge, raw traces or platform identifiers.

## Production Flags

IP guard, output inspection, capability truth, planning safety, planning
context binding and Business Knowledge Registry are enabled. Self-improvement
direct mutation, proposal application, approval, execution, Calendar
authorisation, Calendar reads, Calendar writes, MCP and external mutations
remain disabled.
