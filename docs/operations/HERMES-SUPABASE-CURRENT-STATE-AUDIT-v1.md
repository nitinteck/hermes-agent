# Hermes Supabase Current State Audit v1

Status: metadata-only current-state audit. No production rows, secrets, or
private payloads are included.

## Supabase Project

- CLI-visible project: `OVOS`
- Project ref: `fpzmvmzxzpkybooileua`
- Region: West Europe
- Local project id in `supabase/config.toml`: `ovos-core`
- Local checkout is not linked to the remote project.

## Local Supabase Configuration

- API enabled on local port `55421`.
- Exposed Data API schemas: `public`, `graphql_public`.
- `ovos` application schema is not exposed via local PostgREST config.
- Local DB port: `55422`.
- Shadow DB port: `55420`.
- PostgreSQL major version: 17.
- Realtime enabled.
- Storage enabled.
- Storage vector feature enabled in config.
- S3 protocol disabled.
- Auth enabled.
- Seed disabled.

## Migration History

Static migration inventory found 17 local migration files through
`20260729130000_hermes_mvp_event_journal_daily_brief.sql`.

| migration | primary domain |
| --- | --- |
| `20260721202828_create_ovos_knowledge_core.sql` | knowledge objects, source records, attachments, relationships, processing events |
| `20260721230736_fix_ovos_recall_headline.sql` | recall function fix |
| `20260724120000_add_ovos_conversation_provenance.sql` | conversations, participants, messages |
| `20260725180157_ovos_005a_conversation_recall.sql` | conversation recall |
| `20260725184235_ovos_005b_conversation_signals.sql` | conversation signals |
| `20260725200102_ovos_005c_conversation_summaries.sql` | summaries |
| `20260725204625_ovos_006a_knowledge_memory.sql` | knowledge memories |
| `20260725224708_ovos_006c_multimodal_evidence_foundation.sql` | evidence items and source links |
| `20260725234408_ovos_006d_networking_memory_mvp.sql` | networking observations and workflow feedback |
| `20260726143000_pm14_executive_context.sql` | executive identity and organisation context |
| `20260728120000_ede_001_foundation.sql` | EDE foundation |
| `20260728130000_ede_003_executive_reasoning.sql` | EDE reasoning |
| `20260728140000_ede_004_organisational_knowledge_graph.sql` | OKG |
| `20260728150000_ede_005_pattern_evolution.sql` | pattern evolution |
| `20260728160000_ede_006_executive_planning_approval.sql` | planning and approval |
| `20260729120000_ede_007a_execution_safety_kernel.sql` | execution safety kernel |
| `20260729130000_hermes_mvp_event_journal_daily_brief.sql` | event journal and daily briefs |

## Static Schema Counts

| object type | count |
| --- | ---: |
| distinct `ovos` tables | 102 |
| functions/RPCs | 48 |
| indexes | 92 |
| triggers | 33 |
| RLS policies | 88 |
| RLS enable statements | 103 static statements |
| Edge Functions | 0 deployed |
| Storage buckets | 1 remote bucket observed |

The RLS enable count comes from static migration parsing and includes repeated
or non-table statements. Treat it as evidence of broad RLS intent, not as a
catalog-certified count. A future linked catalog audit should confirm exact RLS
coverage table by table.

## Storage

Remote Storage metadata returned one private bucket:

- `ovos-private`
- public: `false`

Local config declares an `ovos-private` bucket with `50MiB` file size limit.
The remote bucket metadata response did not report a bucket-level file size
limit. Confirm the effective limit before document ingestion.

## Edge Functions

Remote `supabase functions list` returned an empty list for the project ref.

## Realtime, Queues, Cron, Vector

- Realtime is enabled in local config.
- No application Realtime publications were identified in the migrations during
  this static audit.
- No queue or `pgmq` usage was identified in repository migrations.
- No Supabase Cron usage was identified in repository migrations.
- Storage vector support is enabled in config, but no pgvector extension,
  embedding table, or vector index was identified in migrations.

## Environment References

Repository and VPS metadata reference these variable names only:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OVOS_SUPABASE_SCHEMA`
- `OVOS_CAPTURE_BUCKET`
- `OVOS_MAX_CAPTURE_BYTES`
- `OVOS_TEMP_DIR`
- `OVOS_DEFAULT_TENANT_ID`
- `OVOS_DEFAULT_OWNER_USER_ID`
- `OVOS_DEFAULT_TIMEZONE`

Values were not printed or stored.

## VPS Read-Only Findings

- `hermes-agent` deployed checkout observed at
  `e48afa71693dfbde08448b4a92e0038384773053`.
- `ovos-core` deployed checkout observed at
  `0e6ee394d26ff2d7a814f3c84e0ed920aaaf5232`.
- Gateway Python process and WhatsApp bridge process were observed.
- LiteLLM process was observed on port 4000.
- No `hermes-gateway.service` unit was discoverable through the inspected
  `systemctl` commands.
- `/home/hermes/.hermes` contains local state including `state.db`,
  `sessions/sessions.json`, `executive_orchestrator_traces.jsonl`, logs,
  caches, WhatsApp session files, Markdown memory/profile files, and token/config
  files.
- VPS `ovos-core` checkout was observed ahead of `origin/main`, requiring
  deployment-source reconciliation.

## Backup And Recovery Visibility

No explicit backup, restore-test, retention, or disaster-recovery procedure was
identified from repository files or read-only CLI metadata during this audit.
Stage 0 must confirm backups before any EDP migration.
