# Hermes Google Calendar Context Provider v1

Last updated: 2026-07-29

## Purpose

The Google Calendar Context Provider is Hermes' first live external Executive
Context Provider. It is read-only and exists only to supply bounded calendar
context to the Executive Orchestrator before reasoning.

It does not send invitations, create events, update events, delete events,
write reminders, dispatch adapters, expose Google tools to the LLM, or enable
Hermes live execution.

## Runtime Boundary

Path:

`GatewayRunner._run_agent_inner -> run_reasoning_with_optional_orchestrator -> ExecutiveContextCollectionService -> GoogleCalendarContextProvider -> IntegrationService -> ConnectionRegistry -> CredentialResolver -> GoogleCalendarReadAdapter -> Google Calendar API`

The context provider decides whether Calendar context is useful and normalises
the returned data. It does not own credentials, auth headers, token loading or
connection health. Those are owned by the Integration and Connection Framework.

The LLM receives Hermes-owned `ExecutiveContextContribution` summaries only.
Raw Google API objects, OAuth tokens, refresh tokens, attendee email addresses,
event descriptions, conference URLs and private event details are not supplied
to reasoning context or trace metadata.

## Configuration

Safe defaults keep live reads disabled:

```bash
HERMES_GOOGLE_CALENDAR_CONTEXT_PROVIDER_ENABLED=true
HERMES_GOOGLE_CALENDAR_LIVE_READS_ENABLED=false
HERMES_GOOGLE_CALENDAR_DESCRIPTIONS_ENABLED=false
HERMES_GOOGLE_CALENDAR_TOKEN_FILE=
HERMES_GOOGLE_CALENDAR_CLIENT_SECRET_FILE=
HERMES_GOOGLE_CALENDAR_CONNECTION_ID=google-calendar-primary
HERMES_TENANT_ID=default
HERMES_GOOGLE_CALENDAR_USER_ID=
HERMES_ENVIRONMENT=production
HERMES_GOOGLE_CALENDAR_TIMEZONE=Europe/London
HERMES_GOOGLE_CALENDAR_MAX_EVENTS=25
HERMES_GOOGLE_CALENDAR_MAX_RANGE_DAYS=7
```

`HERMES_GOOGLE_CALENDAR_LIVE_READS_ENABLED=true` may be set only after the
operator has reviewed the OAuth setup and installed user-authorised read-only
credentials on the VPS.

## Scope

The intended OAuth scope is:

`https://www.googleapis.com/auth/calendar.readonly`

Any write-capable scope or API method is out of scope for this provider.

## Selection Rules

Calendar context is selected only for calendar-shaped requests such as:

- meetings today or tomorrow
- next meeting or next event
- diary, agenda, schedule and availability questions
- free-block and conflict checks
- Daily Brief or morning agenda requests

Calendar reads are not selected for unrelated prompts, architecture discussion,
connector planning, or executable requests such as "create a calendar event."
Executable requests still fail closed with `execution_state=not_executed`.

## Query Limits

The provider supports bounded windows only:

- today
- tomorrow
- next event
- next 24 hours
- next 7 days
- maximum configured range: 7 days by default, hard-capped by configuration

Default maximum event count is 25.

## Normalisation

The provider emits:

- `capability_status`
- `schedule_summary`
- `meeting`
- `availability`
- `calendar_conflict`
- `preparation_requirement`

Signals include next meeting, meeting count, scheduled minutes, conflicts,
longest free block, out-of-hours count and preparation hints.

Cancelled events and events declined by the authorised user are excluded from
active schedule calculations. Tentative events remain visible as tentative.
Private events are represented as private calendar events without title,
location or description detail.

## Operator Checks

```bash
hermes executive-orchestrator status
hermes integrations status
hermes executive-orchestrator diagnostic-turn "What meetings do I have today? Answer only from data you actually have."
```

Status output includes Calendar provider enabled state, live-read state,
description-ingestion state, write-capability state and authorisation status.
Integration status includes redacted integration, connection, capability and
adapter state. Neither command includes tokens or event payloads.

## Current Deployment Mode

This milestone may be deployed with the provider installed but not authorised.
In that state Hermes must report:

`AWAITING USER CALENDAR AUTHORISATION`

until a live read is validated against the user's Google Calendar.
