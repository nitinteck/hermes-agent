# Hermes Business Context Ingestion v1

Last updated: 2026-07-30

## Flow

Raw note or document -> classification -> entity extraction -> proposed facts
-> duplicate/conflict detection -> owner-review package -> verified publication
-> retrieval index.

Extracted facts are never verified automatically. In v1, ingestion supports
local YAML, JSON, Markdown and plain text sources only. No external connector,
document crawling, email ingestion or Google Drive integration is enabled.

## Output

Ingestion returns proposed facts and an owner-review package. Publication status
remains `owner_review_required` until a separate owner review explicitly
verifies records.
