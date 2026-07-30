# Hermes Document And Storage Architecture v1

Status: target design.

## Recommendation

Use Supabase Storage for Hermes v1 with private buckets and PostgreSQL metadata.
Move to hybrid Supabase Storage plus external S3 only when volume, file size,
lifecycle, cost, or portability thresholds justify the added complexity.

## Comparison

| criterion | Supabase Storage | External S3 | Hybrid |
| --- | --- | --- | --- |
| RLS integration | strongest with Supabase Auth/metadata | requires custom policy layer | mixed |
| signed URLs | built in | built in, more plumbing | both |
| lifecycle management | adequate for v1 | stronger | stronger for archive tiers |
| backup/restore | tied to Supabase project | independent object controls | split responsibility |
| portability | moderate lock-in | higher portability | most complex |
| file size/volume | good early fit | better at high scale | migration path |
| operational complexity | lowest | medium | highest |
| cost control | simple early | better at large scale | best when mature |

## Object Storage Contents

- original uploaded files;
- WhatsApp/media attachments retained as evidence;
- rendered document exports;
- extraction artifacts where needed;
- thumbnails/previews where useful;
- redacted derivatives;
- large connector payload archives only when policy allows.

## PostgreSQL Metadata

Tables under `documents` should own:

- document identity and tenant ownership;
- object bucket/key and checksum;
- original filename, MIME type, byte size;
- source system and source event;
- document version;
- sensitivity and disclosure policy;
- retention class, deletion state, legal hold;
- ingestion, extraction, chunking, and embedding status;
- deduplication group;
- access policy;
- evidence links.

## Lifecycle

1. Metadata row created with idempotency key.
2. Upload initiated with signed URL.
3. Object checksum verified.
4. Extraction queued.
5. Chunks created.
6. Embeddings created.
7. Retrieval metadata marked current.
8. Retention, deletion, or legal hold decisions recorded.

Deletion must tombstone the document, remove or revoke object access, remove
chunks and embeddings from retrieval, and preserve only the required audit
record.

## Current State Note

The remote project currently exposes a private `ovos-private` bucket. Local
configuration declares a 50 MiB bucket limit, while remote bucket metadata did
not report a bucket-level file size limit through the inspected API response.
Confirm the effective production policy before high-volume document ingestion.
