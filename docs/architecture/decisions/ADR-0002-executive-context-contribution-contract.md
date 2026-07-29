# ADR-0002: Executive Context Contribution Contract

Status: accepted

Date: 2026-07-29

## Decision

All executive context must be represented as validated contributions with
provenance, scope, evidence references, sensitivity and freshness metadata.

## Rationale

Hermes needs to distinguish known facts, inferences and missing information
without dumping raw private data or relying on untraceable model memory.

## Consequences

Providers may contribute bounded summaries and safe references only. Raw
messages, full prompts, secrets and private payloads must not appear in trace
metadata.
