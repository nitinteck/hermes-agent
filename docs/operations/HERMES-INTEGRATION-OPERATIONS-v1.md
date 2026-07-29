# Hermes Integration Operations v1

Last updated: 2026-07-29

## Status Checks

Run:

```bash
hermes integrations status
hermes executive-orchestrator status
```

Expected safety invariants:

- `external_execution=not_executed`
- `live_execution_enabled=false`
- `outbound_writes_enabled=false`
- Google Calendar write capability disabled
- MCP adapter disabled unless deliberately testing the disabled boundary

Status output must not include API keys, OAuth access tokens, refresh tokens,
phone numbers, raw prompts or raw event payloads.

## Google Calendar Authorisation

Calendar reads remain disabled unless:

- `HERMES_GOOGLE_CALENDAR_CONTEXT_PROVIDER_ENABLED=true`
- `HERMES_GOOGLE_CALENDAR_LIVE_READS_ENABLED=true`
- `HERMES_GOOGLE_CALENDAR_TOKEN_FILE` points to an authorised token file
- the token was granted only the read-only Calendar scope

Before these are true, Hermes may describe the provider as installed or awaiting
authorisation, but it must not read Calendar events.

## OpenRouter Diagnostic Failures

If the diagnostic path is configured for OpenRouter without credentials,
Hermes now reports:

`invalid_reason=reasoning_provider_authentication_failed`

This is a reasoning-provider configuration failure, not a Calendar-provider
failure. The diagnostic run is not accepted as a behavioural baseline.

## No-Execution Boundary

This milestone does not enable:

- Calendar writes
- Gmail reads or writes
- ClickUp reads or writes
- Slack/WhatsApp connector reads beyond existing transport handling
- webhooks
- MCP execution
- external action adapters

Potential execution requests must remain declarative and non-executing.
