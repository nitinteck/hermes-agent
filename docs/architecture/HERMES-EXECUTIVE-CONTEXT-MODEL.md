# Hermes Executive Context Model

Status: Slice 2 implementation note

## Contract

`ExecutiveContext` is the immutable, versioned data object supplied to reasoning
turns. It is assembled by `ExecutiveContextResolver` through an
`ExecutiveContextRepository`.

Version:

```text
hermes.executive_context.v1
```

The model is serialisable and contains data only.

## Sections

| Section | Meaning |
| --- | --- |
| `identity` | Authenticated actor and resolved tenant context |
| `organisation` | Organisation, brand, people, roles, and relationship context |
| `strategic` | Current objectives, initiatives, projects, and plans |
| `operational` | Commitments, risks, decisions, approvals, execution requests, and journal events |
| `governance` | Capability Truth, improvement proposal summaries, and safety constraints |
| `knowledge` | Verified facts and evidence metadata where already available |

Each `ExecutiveContextRecord` includes:

- `record_id`
- `category`
- `source_table`
- `source_ref`
- `title`
- `summary`
- `confidence`
- `sensitivity`
- `observed_at`
- `evidence_refs`
- safe metadata

Records without explicit evidence references receive a synthetic metadata-only
evidence reference derived from `source_table` and `source_ref`. This keeps
traceability intact without exposing payload content.

## Limits

The repository and model apply deterministic per-request limits:

| Limit | Default |
| --- | ---: |
| journal records | 5 |
| brief items | 5 |
| decisions | 5 |
| approvals | 5 |
| execution requests | 5 |
| risks | 5 |
| opportunities | 5 |
| rendered context size | 6000 characters |

Operational records use the combined operational budget. Governance is capped at
32 records so Capability Truth and proposal status remain available without
flooding the prompt.

## Reasoning Rendering

Rendered context is labelled as authoritative executive context, not hidden
instructions. It includes:

- version
- correlation id
- request classification
- tenant and actor digests
- authentication state
- execution boundary
- source-labelled records
- warnings and degraded state where applicable

Untrusted user content remains in the separate `Current user request
(untrusted)` section. Secrets and token-shaped values are redacted before
rendering.

## Trace Shape

Safe trace metadata includes:

- context version
- correlation id
- request classification
- tenant and actor digests
- source counts
- record source tables and refs
- evidence ids
- warnings
- degraded state
- context digest

It does not include:

- access tokens
- API keys
- phone numbers
- full prompts
- raw private message history
- database credentials
- repository connections

## Intelligence Compatibility

`ExecutiveContext.to_provider_snapshot()` adapts repository records into the
existing Executive Intelligence snapshot contract. This is a compatibility
adapter over immutable data, not a second source of context.

Records may carry a safe `context_type` metadata value such as `meeting` or
`commitment` so deterministic intelligence modules can interpret EDP-derived
facts without querying independent runtime providers.
