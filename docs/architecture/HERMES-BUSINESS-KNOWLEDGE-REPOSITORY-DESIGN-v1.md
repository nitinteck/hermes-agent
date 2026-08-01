# Hermes Business Knowledge Repository Design v1

Status: Slice 3 review candidate.

## Runtime Contracts

Implementation:

- `gateway/business_knowledge_repository.py`

Contracts:

- `BusinessKnowledgeRepository`;
- `BusinessFactRepository`;
- `BusinessEntityRepository`;
- `EvidenceRepository`;
- `BusinessKnowledgeResolver`.

`ExecutiveContextRepository` consumes `BusinessKnowledgeResolver` and converts
the returned immutable snapshot into `ExecutiveContextRecord` objects. Reasoning
only sees labelled context. It never receives repository objects, database
clients, SQL, RPC handles, or lazy loaders.

## Public RPCs

The Supabase repository calls:

- `public.ovos_bk_search_entities`;
- `public.ovos_bk_search_facts`;
- `public.ovos_bk_list_evidence`;
- `public.ovos_bk_import_dry_run`.

All calls include tenant and owner identifiers. Sensitive records are excluded
by default. The repository has no connector, browser, shell, or external action
surface.

## Failure Behavior

Business Knowledge failures become a scoped warning:

- `business_knowledge_repository_unavailable`.

They do not fabricate facts and do not degrade the entire Executive Context
repository if identity, organisation, and governance context still load.

Potentially executable requests remain blocked before reasoning by the
Executive Orchestrator.
