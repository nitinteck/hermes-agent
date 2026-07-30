# ADR-0002: Selective Event Sourcing

Status: proposed

Decision: Hermes v1 uses mutable canonical tables, immutable versions, audit
events, and scheduled snapshots. It does not use full event sourcing.

Consequences:

- current-state queries remain simple;
- approvals, action proposals, policy decisions, fact changes, and execution
  receipts remain auditable;
- replay complexity is avoided until domains stabilise.
