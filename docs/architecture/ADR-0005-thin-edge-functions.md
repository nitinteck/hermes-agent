# ADR-0005: Thin Edge Functions

Status: proposed

Decision: Supabase Edge Functions remain thin trusted boundaries for OAuth,
webhook verification, upload initiation, approval-link validation, lightweight
event ingestion, and queue publication.

Consequences:

- reasoning, planning, and long-running orchestration stay in Hermes runtime;
- Edge Functions call narrow RPCs rather than broad service-role CRUD;
- every boundary mutation is idempotent and audited.
