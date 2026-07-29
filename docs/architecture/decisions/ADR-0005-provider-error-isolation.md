# ADR-0005: Provider Error Isolation

Status: accepted

Date: 2026-07-29

## Decision

Context provider failures, timeouts, duplicate records and scope mismatches are
isolated and recorded as warnings.

## Rationale

One provider failure should not corrupt the entire conversation path. Safety
sensitive requests still fail closed through the Orchestrator boundary.

## Consequences

Operator traces show provider status and warnings. The model never receives raw
exceptions or secrets.
