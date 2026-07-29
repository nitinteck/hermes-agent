# ADR-0028: Planning v1 Is Request-Scoped

Decision: v1 full plans are generated per request and not durably persisted by
the CLI.

Reason: persistence, versioning and approval state transitions belong to later
planning/approval milestones.
