# Hermes Canonical Contracts v1

Last updated: 2026-07-29

## Executive Turn

`ExecutiveTurnInput` is the Orchestrator boundary object. It contains tenant,
conversation, actor, platform, message, session metadata, deterministic command
output, trace metadata, and runtime context.

## Prepared Turn

`PreparedExecutiveTurn` contains correlation ID, classification, bounded
executive context, evidence references, safety state, reasoning instructions,
reasoning message, trace metadata, context digest, and warnings.

## Observation

`ExecutiveObservation` records provider/model metadata, response status,
latency, evidence references used, safety result, journal records created,
warnings, and no-execution confirmation.

## Context Provider Metadata

`ExecutiveContextProviderMetadata` identifies provider ID, version, provider
type, supported context types, source mechanism, enabled state, deterministic
state, external-data usage, timeout, sensitivity, and health state.

## Context Contribution

`ExecutiveContextContribution` is the canonical unit of executive context. It
must carry provenance and scope and must be renderable as a redacted
`ContextItem`.

## Evidence Reference

`ContextEvidenceReference` links a contribution to a safe source reference,
observed time, provider and digest. Evidence references are identifiers, not
raw payloads.

## Context Snapshot

`ExecutiveContextSnapshot` is the operator-safe collection result. It records
which providers were consulted, contribution counts, warnings, latency and
digests. It is exposed in diagnostics and trace metadata.

## Forbidden Contract Behaviour

No context provider contract may:

- invoke a live external adapter;
- send a message;
- create an event;
- create a task;
- modify an external record;
- call a webhook;
- run shell commands;
- dynamically import unauthorised adapters;
- create executable authorisation state.
