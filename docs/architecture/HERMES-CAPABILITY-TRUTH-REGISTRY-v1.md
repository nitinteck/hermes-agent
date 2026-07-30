# Hermes Capability Truth Registry v1

Last updated: 2026-07-30

## Purpose

Capability Truth is the deterministic source for user-facing capability claims.
The model may reason over supplied capability context, but it must not invent
availability, authorisation or execution status.

## Production Values

- Planning available: true
- Planning execution: false
- Calendar read: false
- Calendar write: false
- Calendar authorised: false
- Email read: false
- Email send: false
- Task read/write: false
- Reminder scheduling: false
- External execution: false
- Approval recording: false
- MCP execution: false
- Shell execution: false
- Webhook execution: false
- Self-modification application: false

## User Language

Use plain language:

- `No Google Calendar account is currently authorised.`
- `I cannot access your live Calendar yet.`
- `Hermes has no enabled email-sending capability, so it should have sent none.`
- `Reminder scheduling is not currently enabled.`

Avoid internal terms such as adapters, execution boundary, registry state or
not_executed contracts in normal WhatsApp.
