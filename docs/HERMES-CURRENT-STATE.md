# Hermes Current State

Last verified: 2026-07-29T16:14:31Z

This is the authoritative current-state entrypoint for the deployed Hermes
runtime. Historical checkpoint records remain useful as snapshots, but this
document is the first place to check for current production behaviour.

## Product Purpose

Hermes is Nitin's intelligent WhatsApp personal assistant. The current product
focus is behavioural readiness: prove the existing Executive Orchestrator,
OVOS/EDE context, Daily Brief, Event Journal and Safety Kernel behave reliably
before adding Gmail, Google Calendar, ClickUp or other read-only connectors.

## Current Phase

HERMES BEHAVIOURAL READINESS & BASELINE STABILISATION v1.

Next approved milestone:

`HERMES MVP v0.2 - READ-ONLY EXECUTIVE CONTEXT CONNECTORS`

## Production Architecture

Production host alias: `hermes-vps`

Runtime paths:

- `hermes-agent`: `/opt/ai-stack/hermes-agent`
- `ovos-core`: `/opt/ai-stack/ovos-core`
- service: user-scoped `hermes-gateway.service`
- service command:
  `/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main gateway run`
- WhatsApp bridge:
  `/usr/bin/node /opt/ai-stack/hermes-agent/scripts/whatsapp-bridge/bridge.js --port 3000 --session /home/hermes/.hermes/whatsapp/session --mode self-chat`

Deployed SHAs:

- `hermes-agent`: `ba4e72b24bd584521e25ea88a7f8dbdd316560fb`
- `ovos-core`: `f978dfdf8e211659cac247f57ec813c965a07bd3`

Production migrations are current through `20260729130000`.

Configured reasoning path:

- provider: custom endpoint
- base URL: `http://localhost:4000/v1`
- model: `gpt-4.1-mini`

## Message Path

Normal production reasoning turns follow:

1. `GatewayRunner._handle_message`
2. `authorized_gateway_dispatch`
3. `GatewayRunner._run_agent_inner`
4. `ExecutiveOrchestrator.prepare_turn`
5. `AIAgent.run_conversation`
6. `ExecutiveOrchestrator.observe_response`
7. existing gateway response delivery

The gateway owns transport, auth, platform normalization, session persistence
and outbound delivery. The Executive Orchestrator owns classification, bounded
context assembly, safety-state construction, reasoning request construction,
post-response observation and trace metadata.

## Active Capabilities

- WhatsApp ingress through the existing bridge.
- Executive Orchestrator enabled for normal production chat.
- Deterministic OVOS hook coexistence where existing gateway dispatch supports
  it.
- Local Event Journal and Daily Brief data surfaces.
- Declarative EDE planning, approvals and action proposals.
- Execution Safety Kernel diagnostics and non-execution controls.
- Local-only diagnostic turn for operator validation.
- Redacted Executive Orchestrator trace lookup.

## Unavailable Capabilities

Hermes currently has no live connector for:

- Gmail
- Google Calendar
- ClickUp
- Slack
- CRM records
- live news
- investment portfolio data
- holidays or travel bookings
- live external execution

Hermes must not claim it can see meetings, email, ClickUp tasks, news,
portfolio positions or bookings unless that information is already present in
current OVOS context.

## Executive Context Sources

The current Orchestrator uses only local and persistent Hermes/OVOS data:

- current gateway turn metadata
- recent Event Journal records
- latest Daily Brief records when available
- approval-like Event Journal records
- execution/action-like records in non-executable states
- risk-like records
- opportunity-like records
- deterministic OVOS command output when supplied

No new read-only connectors are active in this phase.

## Context Limits

Defaults:

- journal records: 5
- brief items: 5
- decisions: 5
- approvals: 5
- execution requests: 5
- risks: 5
- opportunities: 5
- rendered context: 6000 characters

Context is tenant-filtered where tenant IDs are present. Secret-like strings
are redacted before context is rendered.

## Request Classifications

Current deterministic classifications:

- `ordinary_conversation`
- `executive_status`
- `decision_support`
- `planning_request`
- `approval_related`
- `daily_brief`
- `deterministic_ovos_command`
- `potentially_executable`
- `unsupported_or_unsafe`

Classification guides context and safety behaviour. It is not a machine
learning intent framework.

## Safety State

Execution boundary: `not_executed`

Live execution enabled: false

Potentially executable requests fail closed before model invocation with the
external-execution-unavailable message. Post-reasoning responses that imply
external execution occurred are rewritten to the same boundary message.

Action proposals, execution requests, handoff drafts and Daily Brief generated
actions remain declarative and non-executable.

## Test Status

Focused Orchestrator, readiness, deployment and trace-correlation tests pass in
the local repo venv. Full repository baseline is intentionally measured in
`docs/HERMES-TEST-BASELINE.md` and
`docs/generated/hermes-test-baseline.json` because repo-wide validation still
contains pre-existing debt unrelated to this milestone.

Known technical debt:

- hermes-agent repo-wide `ruff format --check` has pre-existing formatting
  debt.
- hermes-agent local `python3` on macOS is Python 3.9 and cannot import the
  project; use `.venv/bin/python` or Python 3.11+.
- Historical docs in `ovos-core/docs/PM*.md` and `OVOS-00*.md` are snapshots
  and may say "not deployed" for milestones that were not production-current
  at the time.

## Production Verification Commands

Run from the VPS unless noted:

```bash
systemctl --user is-active hermes-gateway.service
systemctl --user show hermes-gateway.service -p ActiveState -p SubState -p ExecMainPID --no-pager
git -C /opt/ai-stack/hermes-agent rev-parse HEAD
git -C /opt/ai-stack/ovos-core rev-parse HEAD
/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main executive-orchestrator status
/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main executive-orchestrator diagnostic-turn "Hermes diagnostic: confirm orchestrator health."
/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main executive-orchestrator trace-lookup --approx-timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --window-seconds 900
cd /opt/ai-stack/ovos-core && npx supabase migration list --linked
```

Do not print `.env.supabase`, API keys, phone numbers, complete prompts or
private message text during verification.
