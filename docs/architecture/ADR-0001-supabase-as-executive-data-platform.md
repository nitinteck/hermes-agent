# ADR-0001: Supabase As Canonical Executive Data Platform

Status: proposed

Decision: Supabase PostgreSQL is the canonical durable Executive Data Platform
for Hermes v1.

Consequences:

- durable business, governance, planning, approval, audit, evidence, capability,
  integration, and executive-state records live in PostgreSQL;
- Hermes runtime becomes progressively stateless where practical;
- local files remain only for runtime/secrets/cache/transport state until
  intentionally migrated;
- application-level filters do not replace RLS.
