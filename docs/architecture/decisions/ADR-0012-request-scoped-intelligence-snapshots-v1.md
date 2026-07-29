# ADR-0012: Intelligence snapshots are request-scoped in v1

Date: 2026-07-29

Status: Accepted

Decision: v1 does not persist full intelligence snapshots. It records safe
trace metadata only.

Consequence: trend analysis and durable intelligence history are future work,
not implicit memory writes.
