# ADR-0004: No Execution in the Context Foundation

Status: accepted

Date: 2026-07-29

## Decision

The Executive Context Provider Framework may read local internal context and
produce declarative evidence only. It must not execute actions.

## Rationale

Behavioural testing and read-only context must be stabilised before controlled
external execution is considered.

## Consequences

Requests that imply sending, creating, scheduling, dispatching, modifying or
deleting external records remain blocked with `execution_state=not_executed`.
