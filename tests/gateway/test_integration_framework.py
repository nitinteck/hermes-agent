from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from gateway.integrations import (
    ActorScope,
    ConnectionDefinition,
    ConnectionRegistry,
    CredentialReference,
    EnvironmentCredentialResolver,
    IntegrationAdapterMetadata,
    IntegrationAdapterRegistry,
    IntegrationCapability,
    IntegrationDefinition,
    IntegrationErrorCode,
    IntegrationRequest,
    IntegrationService,
    IntegrationState,
    InMemoryCapabilityRegistry,
    ResolvedCredential,
)


TENANT = "tenant-1"
USER = "user-1"


class RecordingReadAdapter:
    metadata = IntegrationAdapterMetadata(
        adapter_id="calendar_google_rest",
        integration_id="google_calendar",
        version="1.0.0",
        authentication_types=("oauth_bearer",),
        supported_capability_ids=("calendar.events.read",),
        uses_external_data=True,
        deterministic=True,
        timeout_seconds=2.0,
        retry_max_attempts=1,
        sensitivity="private",
    )

    def __init__(self, *, response: dict | None = None) -> None:
        self.calls: list[
            tuple[IntegrationRequest, ConnectionDefinition, ResolvedCredential]
        ] = []
        self.response = response or {"items": [{"id": "evt-1"}]}

    def execute_read(
        self,
        request: IntegrationRequest,
        connection: ConnectionDefinition,
        credential: ResolvedCredential,
    ) -> dict:
        self.calls.append((request, connection, credential))
        return self.response


def _definition() -> IntegrationDefinition:
    return IntegrationDefinition(
        integration_id="google_calendar",
        display_name="Google Calendar",
        integration_type="native_api",
        version="1.0.0",
        environment="test",
    )


def _connection(
    *,
    connection_id: str = "conn-calendar",
    tenant_id: str = TENANT,
    user_id: str | None = USER,
    status: str = IntegrationState.CONNECTED,
    credential_ref: CredentialReference | None = None,
) -> ConnectionDefinition:
    return ConnectionDefinition(
        connection_id=connection_id,
        integration_id="google_calendar",
        owner_tenant_id=tenant_id,
        owner_user_id=user_id,
        connection_name="Default Calendar",
        authentication_method="oauth_bearer",
        scopes=("https://www.googleapis.com/auth/calendar.readonly",),
        status=status,
        enabled=True,
        created_at="2026-07-29T20:00:00Z",
        credential_ref=credential_ref
        or CredentialReference(
            credential_ref_id="cred-calendar",
            integration_id="google_calendar",
            tenant_id=tenant_id,
            user_id=user_id,
            environment="test",
            source="env",
            key="TEST_GOOGLE_CALENDAR_TOKEN",
        ),
        capability_ids=("calendar.events.read",),
        environment="test",
    )


def _capability(
    *,
    capability_id: str = "calendar.events.read",
    read_write: str = "read",
    enabled: bool = True,
) -> IntegrationCapability:
    return IntegrationCapability(
        capability_id=capability_id,
        integration_id="google_calendar",
        adapter_id="calendar_google_rest",
        operation_name="events.list",
        category="context_read",
        read_write=read_write,
        risk_class="low",
        required_scopes=("https://www.googleapis.com/auth/calendar.readonly",),
        required_permissions=(),
        required_approval_class="none",
        input_schema_ref="google_calendar.events.read.v1",
        output_schema_ref="google_calendar.events.v1",
        tenant_scope="tenant",
        user_scope="user",
        enabled=enabled,
        environment="test",
        health_dependency="google_calendar",
        lifecycle_state="active",
    )


def _service(monkeypatch, *, connection: ConnectionDefinition | None = None):
    monkeypatch.setenv("TEST_GOOGLE_CALENDAR_TOKEN", "secret-calendar-token")
    connections = ConnectionRegistry()
    connections.register_integration(_definition())
    connections.register_connection(connection or _connection())
    capabilities = InMemoryCapabilityRegistry()
    capabilities.register(_capability())
    adapters = IntegrationAdapterRegistry()
    adapter = RecordingReadAdapter()
    adapters.register(adapter)
    service = IntegrationService(
        connection_registry=connections,
        capability_registry=capabilities,
        adapter_registry=adapters,
        credential_resolver=EnvironmentCredentialResolver(),
    )
    return service, connections, adapter


def test_connection_registry_enforces_tenant_user_scope_and_rejects_secret_metadata() -> (
    None
):
    registry = ConnectionRegistry()
    registry.register_integration(_definition())
    connection = _connection()
    registry.register_connection(connection)

    assert (
        registry.get(
            "conn-calendar", actor_scope=ActorScope(TENANT, USER)
        ).connection_id
        == "conn-calendar"
    )
    assert registry.list_by_tenant(TENANT)[0].connection_id == "conn-calendar"
    assert registry.list_by_user(TENANT, USER)[0].connection_id == "conn-calendar"
    assert (
        registry.list_by_integration("google_calendar")[0].connection_id
        == "conn-calendar"
    )

    with pytest.raises(ValueError, match="tenant_scope_violation"):
        registry.get("conn-calendar", actor_scope=ActorScope("tenant-2", USER))
    with pytest.raises(ValueError, match="user_scope_violation"):
        registry.get("conn-calendar", actor_scope=ActorScope(TENANT, "user-2"))
    with pytest.raises(ValueError, match="secret"):
        registry.register_connection(
            _connection(connection_id="leaky").with_updates(
                safe_metadata={"access_token": "secret-calendar-token"}
            )
        )


def test_capability_registry_describes_but_service_rejects_external_write(
    monkeypatch,
) -> None:
    service, _connections, _adapter = _service(monkeypatch)
    service.capability_registry.register(
        _capability(capability_id="calendar.events.create", read_write="write")
    )

    result = service.execute_read(
        IntegrationRequest(
            capability_id="calendar.events.create",
            connection_id="conn-calendar",
            actor_scope=ActorScope(TENANT, USER),
            parameters={"summary": "Must not be created"},
            trace_context={"correlation_id": "test"},
        )
    )

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code == IntegrationErrorCode.UNSUPPORTED_OPERATION
    assert _adapter.calls == []
    assert "secret-calendar-token" not in json.dumps(result.safe_trace())


def test_credential_resolver_returns_secret_boundary_object_without_repr_leak(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TEST_GOOGLE_CALENDAR_TOKEN", "secret-calendar-token")
    resolver = EnvironmentCredentialResolver()
    credential = resolver.resolve(
        CredentialReference(
            credential_ref_id="cred-calendar",
            integration_id="google_calendar",
            tenant_id=TENANT,
            user_id=USER,
            environment="test",
            source="env",
            key="TEST_GOOGLE_CALENDAR_TOKEN",
        ),
        actor_scope=ActorScope(TENANT, USER, environment="test"),
    )

    assert credential.value == "secret-calendar-token"
    assert "secret-calendar-token" not in repr(credential)
    assert "secret-calendar-token" not in json.dumps(credential.safe_trace())


def test_integration_service_execute_read_updates_health_and_safe_trace(
    monkeypatch,
) -> None:
    service, connections, adapter = _service(monkeypatch)

    result = service.execute_read(
        IntegrationRequest(
            capability_id="calendar.events.read",
            connection_id="conn-calendar",
            actor_scope=ActorScope(TENANT, USER, environment="test"),
            parameters={"window": "today"},
            trace_context={"correlation_id": "corr-1"},
        )
    )

    assert result.status == "ok"
    assert result.data == {"items": [{"id": "evt-1"}]}
    assert len(adapter.calls) == 1
    assert adapter.calls[0][2].value == "secret-calendar-token"
    connection = connections.get(
        "conn-calendar", actor_scope=ActorScope(TENANT, USER, environment="test")
    )
    assert connection.health.status == "healthy"
    assert connection.last_success_at is not None
    trace = result.safe_trace()
    assert trace["integration_id"] == "google_calendar"
    assert trace["capability_id"] == "calendar.events.read"
    assert trace["connection_state"] == IntegrationState.CONNECTED
    assert trace["credential_resolved"] is True
    assert "secret-calendar-token" not in json.dumps(trace)


def test_integration_service_fails_closed_for_unknown_disabled_or_unscoped_access(
    monkeypatch,
) -> None:
    service, _connections, adapter = _service(monkeypatch)

    unknown = service.execute_read(
        IntegrationRequest(
            capability_id="calendar.events.unknown",
            connection_id="conn-calendar",
            actor_scope=ActorScope(TENANT, USER),
            parameters={},
            trace_context={},
        )
    )
    wrong_tenant = service.execute_read(
        IntegrationRequest(
            capability_id="calendar.events.read",
            connection_id="conn-calendar",
            actor_scope=ActorScope("tenant-2", USER),
            parameters={},
            trace_context={},
        )
    )

    assert unknown.error is not None
    assert unknown.error.code == IntegrationErrorCode.UNSUPPORTED_OPERATION
    assert wrong_tenant.error is not None
    assert wrong_tenant.error.code == IntegrationErrorCode.TENANT_SCOPE_VIOLATION
    assert adapter.calls == []


def test_integration_service_missing_credential_and_auth_required_are_safe(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TEST_GOOGLE_CALENDAR_TOKEN", raising=False)
    service, connections, adapter = _service(monkeypatch)
    connections.update_connection_state(
        "conn-calendar",
        IntegrationState.AUTHORISATION_REQUIRED,
        actor_scope=ActorScope(TENANT, USER),
    )

    result = service.execute_read(
        IntegrationRequest(
            capability_id="calendar.events.read",
            connection_id="conn-calendar",
            actor_scope=ActorScope(TENANT, USER),
            parameters={},
            trace_context={},
        )
    )

    assert result.error is not None
    assert result.error.code == IntegrationErrorCode.DISABLED
    assert result.safe_trace()["credential_resolved"] is False
    assert adapter.calls == []


def test_connection_health_records_failure_without_secret_leak(monkeypatch) -> None:
    service, connections, _adapter = _service(monkeypatch)
    now = datetime(2026, 7, 29, 20, 30, tzinfo=timezone.utc).isoformat()

    updated = connections.record_failure(
        "conn-calendar",
        reason_code=IntegrationErrorCode.RATE_LIMITED,
        safe_summary="Upstream returned rate limit",
        checked_at=now,
        actor_scope=ActorScope(TENANT, USER),
    )

    assert updated.health.status == "degraded"
    assert updated.health.reason_code == IntegrationErrorCode.RATE_LIMITED
    assert updated.health.consecutive_failures == 1
    assert "secret" not in json.dumps(updated.safe_metadata).casefold()
    assert service is not None
