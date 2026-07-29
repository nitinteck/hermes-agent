# Hermes Executive Intelligence Operations v1

Last updated: 2026-07-29

Operator commands:

```bash
hermes intelligence status
hermes intelligence modules
hermes intelligence diagnostics
hermes executive-orchestrator status
```

Expected production-safe values:

- Executive Intelligence Engine enabled after validation
- Intelligence Registry enabled
- deterministic modules enabled
- inference modules disabled
- external calls enabled: false
- live execution enabled: false
- execution boundary: `not_executed`
- Calendar live reads disabled until separately authorised
- MCP disabled

Diagnostics use synthetic context only. They do not read Calendar, Gmail,
ClickUp, WhatsApp, Slack, CRM, news or portfolio systems.

Trace output is safe metadata only: selected/successful/failed modules, signal
counts, severity/priority summaries, evidence counts, latency, digest and safe
error codes.
