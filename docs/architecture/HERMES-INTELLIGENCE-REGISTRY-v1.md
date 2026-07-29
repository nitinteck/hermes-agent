# Hermes Intelligence Registry v1

Last updated: 2026-07-29

The Intelligence Registry contains approved deterministic intelligence modules.
It is distinct from Provider, Connection, Capability and future Skill
registries.

Each module declares:

- module ID, name, owner and version
- input and optional context types
- output intelligence types
- deterministic status
- required evidence
- freshness requirements
- minimum context requirements
- tenant/user scope
- timeout, priority, risk and health
- lifecycle status
- calculation documentation
- test fixture references

Supported operations:

- register
- duplicate-ID rejection
- lookup
- enable/disable
- list enabled modules
- filter by input context type
- filter by output intelligence type
- deterministic-only selection
- health inspection

Future modules should use context inputs, not integrations directly. Examples:

- Gmail response-delay intelligence: consumes email metadata context, emits
  response-delay and follow-up-due signals.
- ClickUp project-health intelligence: consumes task/project context, emits
  stalled-project and deadline-risk signals.
- CRM relationship intelligence: consumes relationship context, emits
  inactivity signals.
- Financial cashflow intelligence: consumes authorised finance context, emits
  threshold and variance signals.
- Investment portfolio intelligence: consumes authorised portfolio context,
  emits exposure and movement signals.
- Wellbeing intelligence: consumes authorised wellbeing context, emits
  schedule-load and recovery-risk signals.
- News relevance intelligence: consumes curated news context, emits relevance
  signals.

Model inference, recommendations and forecasts require a future inference
module framework and are disabled in v1.
