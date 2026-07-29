# Hermes Executive Planning Operations v1

Last updated: 2026-07-29

## Operator Commands

```bash
hermes planning status
hermes planning strategies
hermes planning diagnostics
hermes planning plans
hermes executive-orchestrator status
hermes reasoning status
```

Expected production-safe state:

- Planning Engine enabled
- Planning Registry enabled
- deterministic planning enabled
- model-assisted planning disabled
- candidate evaluation enabled
- proposed-action generation enabled as descriptions only
- Approval Engine disabled
- Execution Engine disabled
- Calendar authorisation disabled unless separately verified
- Calendar live reads disabled unless separately authorised
- Calendar writes disabled
- MCP disabled
- external mutations disabled
- live execution disabled
- execution boundary `not_executed`

## Diagnostics

`hermes planning diagnostics` creates a synthetic request-scoped proposed plan
and reports only safe trace metadata. It does not persist full plan content and
does not contact external systems.

`hermes planning plans` reports an empty list in v1 because full plans are not
durably persisted by the CLI.

## Failure Behaviour

Planning failure degrades safely:

- ordinary non-sensitive turns may continue without a Planning Snapshot;
- planning turns receive a limitation or `not_eligible` snapshot;
- executable and unsafe turns remain blocked before external action;
- no fallback may claim approval, execution or completion.

## Production Verification

```bash
systemctl --user is-active hermes-gateway.service
/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main planning status
/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main planning diagnostics
/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main executive-orchestrator diagnostic-turn "Help me plan the next milestone without starting connectors yet."
```

Do not print secrets, `.env` files, raw prompts, phone numbers or private
conversation content during verification.
