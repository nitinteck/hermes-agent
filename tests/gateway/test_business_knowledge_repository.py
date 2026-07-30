from __future__ import annotations

import json
from urllib.parse import urlparse

import pytest

from gateway.business_knowledge_repository import (
    BusinessKnowledgeEntity,
    BusinessKnowledgeFact,
    BusinessKnowledgeRepositoryError,
    BusinessKnowledgeResolver,
    InMemoryBusinessKnowledgeRepository,
    SupabaseBusinessKnowledgeRepository,
)
from gateway.edp_governance import TenantContext


TENANT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_ID = "22222222-2222-4222-8222-222222222222"


def _tenant() -> TenantContext:
    return TenantContext(
        user_id=ACTOR_ID,
        tenant_id=TENANT_ID,
        membership_id="membership-1",
        role="owner",
        channel="diagnostic",
        actor_type="human",
        correlation_id="bk-corr",
    )


def test_in_memory_repository_filters_sensitivity_by_default() -> None:
    repository = InMemoryBusinessKnowledgeRepository(
        entities=(
            BusinessKnowledgeEntity(
                entity_id="entity-1",
                entity_kind="organisation",
                canonical_name="Hermes Build",
                summary="Visible organisation.",
                status="active",
                sensitivity="internal",
            ),
            BusinessKnowledgeEntity(
                entity_id="entity-2",
                entity_kind="person",
                canonical_name="Confidential Person",
                summary="Sensitive person.",
                status="active",
                sensitivity="confidential",
            ),
        )
    )

    visible = repository.search_entities(tenant_context=_tenant())
    sensitive = repository.search_entities(
        tenant_context=_tenant(),
        include_sensitive=True,
    )

    assert [entity.entity_id for entity in visible] == ["entity-1"]
    assert [entity.entity_id for entity in sensitive] == ["entity-1", "entity-2"]


def test_resolver_degrades_without_fabricating_context() -> None:
    resolver = BusinessKnowledgeResolver(
        repository=InMemoryBusinessKnowledgeRepository(available=False)
    )

    snapshot = resolver.resolve(tenant_context=_tenant())

    assert snapshot.entities == ()
    assert snapshot.facts == ()
    assert snapshot.evidence == ()
    assert snapshot.warnings == ("business_knowledge_repository_unavailable",)


def test_import_dry_run_is_import_only_and_non_executing() -> None:
    repository = InMemoryBusinessKnowledgeRepository()

    result = repository.dry_run_import(
        tenant_context=_tenant(),
        source_format="yaml",
        source_name="facts.yaml",
        items=({"kind": "fact", "statement": "mission: build hermes edp"},),
        provenance={"file": "facts.yaml"},
        correlation_id="bk-import",
    )

    assert result["runtime_authority"] is False
    assert result["execution_status"] == "not_executed"
    assert repository.import_calls[0]["source_format"] == "yaml"


def test_import_dry_run_rejects_non_import_formats() -> None:
    repository = InMemoryBusinessKnowledgeRepository()

    with pytest.raises(ValueError):
        repository.dry_run_import(
            tenant_context=_tenant(),
            source_format="python",
            source_name="script.py",
            items=(),
        )


def test_supabase_repository_uses_public_business_knowledge_rpcs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_requests = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return json.dumps([]).encode("utf-8")

    def _urlopen(request, timeout):  # noqa: ANN001
        del timeout
        captured_requests.append(request)
        return _Response()

    monkeypatch.setattr(
        "gateway.business_knowledge_repository.urllib.request.urlopen",
        _urlopen,
    )
    repository = SupabaseBusinessKnowledgeRepository(
        supabase_url="https://example.supabase.co",
        api_key="anon-key",
        bearer_token="user-token",
    )

    repository.search_entities(tenant_context=_tenant(), entity_kinds=("organisation",))
    repository.search_facts(tenant_context=_tenant(), fact_types=("mission",))
    repository.list_evidence(tenant_context=_tenant(), fact_id="fact-1")

    paths = [urlparse(request.full_url).path for request in captured_requests]
    assert paths == [
        "/rest/v1/rpc/ovos_bk_search_entities",
        "/rest/v1/rpc/ovos_bk_search_facts",
        "/rest/v1/rpc/ovos_bk_list_evidence",
    ]
    first_payload = json.loads(captured_requests[0].data.decode("utf-8"))
    assert first_payload["p_tenant_id"] == TENANT_ID
    assert first_payload["p_owner_user_id"] == ACTOR_ID
    assert first_payload["p_entity_kinds"] == ["organisation"]
    assert first_payload["p_include_sensitive"] is False


def test_supabase_import_dry_run_preserves_provenance_and_never_executes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_payloads = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ANN001
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "runtime_authority": True,
                    "execution_status": "executed",
                    "candidate_count": 1,
                    "duplicate_count": 0,
                    "conflict_count": 0,
                }
            ).encode("utf-8")

    def _urlopen(request, timeout):  # noqa: ANN001
        del timeout
        captured_payloads.append(json.loads(request.data.decode("utf-8")))
        return _Response()

    monkeypatch.setattr(
        "gateway.business_knowledge_repository.urllib.request.urlopen",
        _urlopen,
    )
    repository = SupabaseBusinessKnowledgeRepository(
        supabase_url="https://example.supabase.co",
        api_key="anon-key",
        bearer_token="user-token",
    )

    result = repository.dry_run_import(
        tenant_context=_tenant(),
        source_format="csv",
        source_name="facts.csv",
        items=({"kind": "entity", "label": "Hermes Build"},),
        provenance={"source_format": "csv"},
        correlation_id="bk-import",
    )

    assert result["runtime_authority"] is False
    assert result["execution_status"] == "not_executed"
    payload = captured_payloads[0]
    assert payload["source_format"] == "csv"
    assert payload["provenance"]["import_only"] is True
    assert payload["provenance"]["runtime_authority"] is False


def test_supabase_repository_errors_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def _urlopen(request, timeout):  # noqa: ANN001
        del request, timeout
        raise TimeoutError("slow")

    monkeypatch.setattr(
        "gateway.business_knowledge_repository.urllib.request.urlopen",
        _urlopen,
    )
    repository = SupabaseBusinessKnowledgeRepository(
        supabase_url="https://example.supabase.co",
        api_key="anon-key",
        bearer_token="user-token",
    )

    with pytest.raises(BusinessKnowledgeRepositoryError):
        repository.search_facts(tenant_context=_tenant())
