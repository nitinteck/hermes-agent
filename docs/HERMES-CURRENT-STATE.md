# Hermes Current State

Last verified: 2026-07-29T19:20:00Z

This is the authoritative current-state entrypoint for the deployed Hermes
runtime. Historical checkpoint records remain useful as snapshots, but this
document is the first place to check for current production behaviour.

## Product Purpose

Hermes is Nitin's intelligent WhatsApp personal assistant. The current product
focus is behavioural readiness: prove the existing Executive Orchestrator,
OVOS/EDE context, Daily Brief, Event Journal, Safety Kernel and first
read-only Calendar context provider behave reliably before adding Gmail,
ClickUp or other read-only connectors.

## Current Phase

HERMES INTEGRATION FRAMEWORK AND EXECUTIVE INTELLIGENCE FOUNDATION v1.

Current foundation capabilities:

- Integration & Connection Framework v1.
- Google Calendar read-only context provider installed with live reads disabled.
- Executive Intelligence Engine v1 deterministic and request-scoped.

Next approved milestone:

`Hermes Executive Reasoning Engine v1`

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

Production runtime SHAs:

- `hermes-agent` runtime-changing SHA:
  `7a7ecdceab5010e5bcf5852ed756f9122e2d3b5b`
- previous runtime-changing Hermes SHA:
  `db818dc4da080321767562de322a0968b063bbef`
- `ovos-core`: `0e6ee394d26ff2d7a814f3c84e0ed920aaaf5232`

The exact deployed checkout SHA may be newer when documentation-only commits
are deployed after runtime validation. The deployment report records the final
checkout SHA.

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
5. `ExecutiveContextCollectionService`
6. `ExecutiveIntelligenceEngine` when enabled
7. `AIAgent.run_conversation`
8. `ExecutiveOrchestrator.observe_response`
9. existing gateway response delivery

The gateway owns transport, auth, platform normalization, session persistence
and outbound delivery. The Executive Orchestrator owns classification, bounded
context assembly, safety-state construction, reasoning request construction,
post-response observation and trace metadata.

## Active Capabilities

- WhatsApp ingress through the existing bridge.
- Executive Orchestrator enabled for normal production chat.
- Executive Context Provider Framework enabled for bounded local context.
- Google Calendar Executive Context Provider installed as a read-only external
  provider. Live reads remain disabled until user Calendar authorisation and
  operator review are complete.
- Executive Intelligence Engine v1 on the feature branch, deterministic and
  request-scoped.
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
- ClickUp
- Slack
- CRM records
- live news
- investment portfolio data
- holidays or travel bookings
- live external execution

Google Calendar has a read-only provider but must report authorisation status
precisely. Hermes must not claim it can see meetings unless live Calendar reads
are authorised or the meeting information is already present in current OVOS
context. Hermes must not claim it can see email, ClickUp tasks, news, portfolio
positions or bookings unless that information is already present in current
OVOS context.

## Executive Context Sources

The current Orchestrator uses only local and persistent Hermes/OVOS data:

- current gateway turn metadata
- recent conversation metadata as digests and source categories
- persistent profile availability metadata
- recent Event Journal records
- latest Daily Brief records when available
- approval-like Event Journal records
- execution/action-like records in non-executable states
- risk-like records
- opportunity-like records
- deterministic OVOS command output when supplied
- Google Calendar schedule context when the Calendar provider is selected and
  live reads are authorised

No new read-only connectors are active in this phase.

Built-in context providers:

- `current_request_metadata`
- `recent_conversation`
- `persistent_profile`

Disabled provider boundaries:

- `mock_executive_context`, test/local only and disabled unless explicitly set
- `mcp_context_boundary`, disabled until the read-only connector milestone

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

## Runtime Flags

Production-safe default flags:

```bash
HERMES_EXECUTIVE_ORCHESTRATOR_ENABLED=true
HERMES_EXECUTIVE_CONTEXT_PROVIDER_FRAMEWORK_ENABLED=true
HERMES_EXECUTIVE_INTELLIGENCE_ENABLED=true
HERMES_INTELLIGENCE_REGISTRY_ENABLED=true
HERMES_DETERMINISTIC_INTELLIGENCE_MODULES_ENABLED=true
HERMES_INFERENCE_INTELLIGENCE_MODULES_ENABLED=false
HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED=false
HERMES_MCP_CONTEXT_ADAPTER_ENABLED=false
```

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
