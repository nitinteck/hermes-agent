# Hermes Business Knowledge Import Design v1

Status: Slice 3 review candidate.

## Principle

YAML, JSON, and CSV are import-only candidate formats. They are never runtime
authority and are never read from disk by the reasoning path.

## Dry Run

`public.ovos_bk_import_dry_run(p_payload jsonb)` accepts a parsed candidate
payload with:

- `tenant_id`;
- `actor_user_id`;
- `source_format` of `yaml`, `json`, or `csv`;
- `source_name`;
- `payload_digest`;
- `items`;
- `provenance`;
- optional `correlation_id`.

The RPC creates a dry-run batch and candidate rows, detects duplicates and
conflicts, preserves provenance, writes bounded audit metadata, and returns:

- `runtime_authority=false`;
- `execution_status=not_executed`;
- candidate, duplicate, and conflict counts.

## Non-Goals

Slice 3 does not parse files, watch folders, run background imports, sync
connectors, or promote candidates to verified facts automatically. Promotion
requires future explicit review workflows.
