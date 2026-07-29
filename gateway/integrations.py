"""Hermes integration, connection and capability framework.

This module provides the shared boundary between executive context providers and
external systems. It is intentionally read-first for v1: write capabilities can
be described, but ``execute_read`` fails closed for anything that is not an
explicit read capability.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import json
import os
import re
import time
from typing import Any, Protocol


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if _looks_secret_key(str(key)) and str(key) not in _SAFE_TRACE_KEYS
            else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        if _looks_secret_value(value):
            return "[REDACTED]"
        return value
    return value


def _looks_secret_key(key: str) -> bool:
    return bool(
        re.search(
            r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|credential|authorization|bearer|header)",
            key,
        )
    )


_SAFE_TRACE_KEYS = {
    "credential_count",
    "credential_ref",
    "credential_ref_id",
    "credential_resolved",
}


def _looks_secret_value(value: str) -> bool:
    lowered = value.casefold()
    if "bearer " in lowered or "secret" in lowered or "token=" in lowered:
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9._=-]{32,}", value))


def _validate_safe_metadata(metadata: Mapping[str, Any]) -> None:
    rendered = json.dumps(metadata, sort_keys=True, default=str)
    for key, value in metadata.items():
        if _looks_secret_key(str(key)):
            raise ValueError("safe_metadata must not contain secret-bearing keys")
        if isinstance(value, str) and _looks_secret_value(value):
            raise ValueError("safe_metadata must not contain secret-bearing values")
    if _looks_secret_value(rendered):
        raise ValueError("safe_metadata must not contain secret-bearing values")


@dataclass(frozen=True)
class ActorScope:
    tenant_id: str
    user_id: str | None = None
    environment: str = "default"


class IntegrationState:
    UNCONFIGURED = "unconfigured"
    DISCONNECTED = "disconnected"
    AUTHORISATION_REQUIRED = "authorisation_required"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    REVOKED = "revoked"
    DISABLED = "disabled"


class IntegrationErrorCode:
    MISSING_CREDENTIALS = "missing_credentials"
    INVALID_CREDENTIALS = "invalid_credentials"
    EXPIRED_CREDENTIALS = "expired_credentials"
    REVOKED_CREDENTIALS = "revoked_credentials"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    PERMISSION_DENIED = "permission_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"
    MALFORMED_RESPONSE = "malformed_response"
    CONFIGURATION_ERROR = "configuration_error"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    DISABLED = "disabled"
    TENANT_SCOPE_VIOLATION = "tenant_scope_violation"
    USER_SCOPE_VIOLATION = "user_scope_violation"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(frozen=True)
class IntegrationDefinition:
    integration_id: str
    display_name: str
    integration_type: str
    version: str
    environment: str = "default"
    lifecycle_state: str = "active"
    safe_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_safe_metadata(self.safe_metadata)


@dataclass(frozen=True)
class CredentialReference:
    credential_ref_id: str
    integration_id: str
    tenant_id: str
    user_id: str | None
    environment: str
    source: str
    key: str
    safe_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_safe_metadata(self.safe_metadata)

    def safe_trace(self) -> dict[str, Any]:
        return {
            "credential_ref_id": self.credential_ref_id,
            "integration_id": self.integration_id,
            "tenant_id": self.tenant_id,
            "user_scoped": self.user_id is not None,
            "environment": self.environment,
            "source": self.source,
            "resolved_key_digest": str(abs(hash((self.source, self.key))))[:12],
            "safe_metadata_keys": sorted(str(key) for key in self.safe_metadata),
        }


@dataclass(frozen=True)
class ResolvedCredential:
    credential_ref_id: str
    integration_id: str
    source: str
    value: str
    resolved_at: str = field(default_factory=_now_iso)
    safe_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            "ResolvedCredential("
            f"credential_ref_id={self.credential_ref_id!r}, "
            f"integration_id={self.integration_id!r}, source={self.source!r}, "
            "value='[REDACTED]')"
        )

    def safe_trace(self) -> dict[str, Any]:
        return {
            "credential_ref_id": self.credential_ref_id,
            "integration_id": self.integration_id,
            "source": self.source,
            "resolved": bool(self.value),
            "resolved_at": self.resolved_at,
            "safe_metadata": _redact(self.safe_metadata),
        }


@dataclass(frozen=True)
class ConnectionHealth:
    status: str = "unknown"
    reason_code: str | None = None
    safe_summary: str | None = None
    checked_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    consecutive_failures: int = 0
    latency_ms: float | None = None
    upstream_status: int | None = None
    authentication_status: str | None = None
    capability_status: str | None = None

    def safe_trace(self) -> dict[str, Any]:
        return _redact({
            "status": self.status,
            "reason_code": self.reason_code,
            "safe_summary": self.safe_summary,
            "checked_at": self.checked_at,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "consecutive_failures": self.consecutive_failures,
            "latency_ms": self.latency_ms,
            "upstream_status": self.upstream_status,
            "authentication_status": self.authentication_status,
            "capability_status": self.capability_status,
        })


@dataclass(frozen=True)
class ConnectionDefinition:
    connection_id: str
    integration_id: str
    owner_tenant_id: str
    owner_user_id: str | None
    connection_name: str
    authentication_method: str
    scopes: tuple[str, ...]
    status: str
    enabled: bool
    created_at: str
    credential_ref: CredentialReference | None = None
    capability_ids: tuple[str, ...] = ()
    environment: str = "default"
    health: ConnectionHealth = field(default_factory=ConnectionHealth)
    safe_metadata: Mapping[str, Any] = field(default_factory=dict)
    last_success_at: str | None = None
    last_failure_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        _validate_safe_metadata(self.safe_metadata)

    def with_updates(self, **kwargs: Any) -> ConnectionDefinition:
        return replace(self, **kwargs)

    def safe_trace(self) -> dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "integration_id": self.integration_id,
            "tenant_id": self.owner_tenant_id,
            "user_scoped": self.owner_user_id is not None,
            "connection_name": self.connection_name,
            "authentication_method": self.authentication_method,
            "scope_count": len(self.scopes),
            "status": self.status,
            "enabled": self.enabled,
            "environment": self.environment,
            "capability_ids": list(self.capability_ids),
            "credential_ref": self.credential_ref.safe_trace()
            if self.credential_ref
            else None,
            "health": self.health.safe_trace(),
            "safe_metadata": _redact(self.safe_metadata),
        }


@dataclass(frozen=True)
class IntegrationCapability:
    capability_id: str
    integration_id: str
    adapter_id: str
    operation_name: str
    category: str
    read_write: str
    risk_class: str
    required_scopes: tuple[str, ...]
    required_permissions: tuple[str, ...]
    required_approval_class: str
    input_schema_ref: str
    output_schema_ref: str
    tenant_scope: str
    user_scope: str
    enabled: bool
    environment: str = "default"
    health_dependency: str | None = None
    lifecycle_state: str = "active"
    safe_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_safe_metadata(self.safe_metadata)

    def safe_trace(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "integration_id": self.integration_id,
            "adapter_id": self.adapter_id,
            "operation_name": self.operation_name,
            "category": self.category,
            "read_write": self.read_write,
            "risk_class": self.risk_class,
            "required_approval_class": self.required_approval_class,
            "enabled": self.enabled,
            "environment": self.environment,
            "lifecycle_state": self.lifecycle_state,
        }


@dataclass(frozen=True)
class IntegrationRequest:
    capability_id: str
    connection_id: str | None
    actor_scope: ActorScope
    parameters: Mapping[str, Any]
    trace_context: Mapping[str, Any] = field(default_factory=dict)
    request_id: str | None = None


@dataclass(frozen=True)
class IntegrationError:
    code: str
    safe_summary: str
    retryable: bool = False
    upstream_status: int | None = None

    def safe_trace(self) -> dict[str, Any]:
        return _redact({
            "code": self.code,
            "safe_summary": self.safe_summary,
            "retryable": self.retryable,
            "upstream_status": self.upstream_status,
        })


@dataclass(frozen=True)
class IntegrationResult:
    status: str
    data: Mapping[str, Any]
    error: IntegrationError | None
    integration_id: str | None
    connection_id: str | None
    capability_id: str
    adapter_id: str | None
    connection_state: str | None
    health_state: str
    latency_ms: float | None
    retry_count: int
    credential_resolved: bool
    audit_metadata: Mapping[str, Any] = field(default_factory=dict)
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)

    def safe_trace(self) -> dict[str, Any]:
        return _redact({
            "status": self.status,
            "integration_id": self.integration_id,
            "connection_id": self.connection_id,
            "capability_id": self.capability_id,
            "adapter_id": self.adapter_id,
            "connection_state": self.connection_state,
            "health_state": self.health_state,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "credential_resolved": self.credential_resolved,
            "error": self.error.safe_trace() if self.error else None,
            "audit_metadata": self.audit_metadata,
            "trace_metadata": self.trace_metadata,
        })


@dataclass(frozen=True)
class IntegrationAdapterMetadata:
    adapter_id: str
    integration_id: str
    version: str
    authentication_types: tuple[str, ...]
    supported_capability_ids: tuple[str, ...]
    uses_external_data: bool
    deterministic: bool
    timeout_seconds: float
    retry_max_attempts: int
    sensitivity: str

    def safe_trace(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "integration_id": self.integration_id,
            "version": self.version,
            "authentication_types": list(self.authentication_types),
            "supported_capability_ids": list(self.supported_capability_ids),
            "uses_external_data": self.uses_external_data,
            "deterministic": self.deterministic,
            "timeout_seconds": self.timeout_seconds,
            "retry_max_attempts": self.retry_max_attempts,
            "sensitivity": self.sensitivity,
        }


class IntegrationAdapter(Protocol):
    metadata: IntegrationAdapterMetadata

    def execute_read(
        self,
        request: IntegrationRequest,
        connection: ConnectionDefinition,
        credential: ResolvedCredential,
    ) -> Mapping[str, Any]: ...


class IntegrationCredentialError(RuntimeError):
    def __init__(self, code: str, safe_summary: str) -> None:
        super().__init__(safe_summary)
        self.code = code
        self.safe_summary = safe_summary


class ConnectionRegistry:
    def __init__(self) -> None:
        self._integrations: dict[str, IntegrationDefinition] = {}
        self._connections: dict[str, ConnectionDefinition] = {}

    def register_integration(self, definition: IntegrationDefinition) -> None:
        if definition.integration_id in self._integrations:
            raise ValueError(f"duplicate integration_id: {definition.integration_id}")
        self._integrations[definition.integration_id] = definition

    def list_integrations(self) -> list[IntegrationDefinition]:
        return sorted(self._integrations.values(), key=lambda item: item.integration_id)

    def register_connection(self, connection: ConnectionDefinition) -> None:
        if connection.integration_id not in self._integrations:
            raise ValueError(f"unknown integration_id: {connection.integration_id}")
        if connection.connection_id in self._connections:
            raise ValueError(f"duplicate connection_id: {connection.connection_id}")
        _validate_safe_metadata(connection.safe_metadata)
        self._connections[connection.connection_id] = connection

    def get(
        self,
        connection_id: str,
        *,
        actor_scope: ActorScope | None = None,
    ) -> ConnectionDefinition:
        connection = self._connections[connection_id]
        if actor_scope is not None:
            self._validate_actor_scope(connection, actor_scope)
        return connection

    def list_by_tenant(self, tenant_id: str) -> list[ConnectionDefinition]:
        return sorted(
            (
                connection
                for connection in self._connections.values()
                if connection.owner_tenant_id == tenant_id
            ),
            key=lambda item: item.connection_id,
        )

    def list_by_user(self, tenant_id: str, user_id: str) -> list[ConnectionDefinition]:
        return sorted(
            (
                connection
                for connection in self._connections.values()
                if connection.owner_tenant_id == tenant_id
                and connection.owner_user_id == user_id
            ),
            key=lambda item: item.connection_id,
        )

    def list_by_integration(self, integration_id: str) -> list[ConnectionDefinition]:
        return sorted(
            (
                connection
                for connection in self._connections.values()
                if connection.integration_id == integration_id
            ),
            key=lambda item: item.connection_id,
        )

    def find_eligible_connection(
        self,
        *,
        integration_id: str,
        actor_scope: ActorScope,
        capability_id: str,
    ) -> ConnectionDefinition | None:
        for connection in self.list_by_integration(integration_id):
            try:
                self._validate_actor_scope(connection, actor_scope)
            except ValueError:
                continue
            if capability_id not in connection.capability_ids:
                continue
            if (
                actor_scope.environment != "default"
                and connection.environment != actor_scope.environment
            ):
                continue
            return connection
        return None

    def update_connection_state(
        self,
        connection_id: str,
        status: str,
        *,
        actor_scope: ActorScope | None = None,
    ) -> ConnectionDefinition:
        connection = self.get(connection_id, actor_scope=actor_scope)
        updated = connection.with_updates(status=status, updated_at=_now_iso())
        self._connections[connection_id] = updated
        return updated

    def record_success(
        self,
        connection_id: str,
        *,
        checked_at: str | None = None,
        latency_ms: float | None = None,
        actor_scope: ActorScope | None = None,
    ) -> ConnectionDefinition:
        connection = self.get(connection_id, actor_scope=actor_scope)
        timestamp = checked_at or _now_iso()
        health = replace(
            connection.health,
            status="healthy",
            reason_code=None,
            safe_summary="Last read succeeded",
            checked_at=timestamp,
            last_success_at=timestamp,
            consecutive_failures=0,
            latency_ms=latency_ms,
        )
        updated = connection.with_updates(
            health=health,
            last_success_at=timestamp,
            last_failure_at=connection.last_failure_at,
            updated_at=timestamp,
        )
        self._connections[connection_id] = updated
        return updated

    def record_failure(
        self,
        connection_id: str,
        *,
        reason_code: str,
        safe_summary: str,
        checked_at: str | None = None,
        latency_ms: float | None = None,
        upstream_status: int | None = None,
        actor_scope: ActorScope | None = None,
    ) -> ConnectionDefinition:
        connection = self.get(connection_id, actor_scope=actor_scope)
        timestamp = checked_at or _now_iso()
        health = replace(
            connection.health,
            status="degraded",
            reason_code=reason_code,
            safe_summary=str(_redact(safe_summary)),
            checked_at=timestamp,
            last_failure_at=timestamp,
            consecutive_failures=connection.health.consecutive_failures + 1,
            latency_ms=latency_ms,
            upstream_status=upstream_status,
        )
        updated = connection.with_updates(
            health=health,
            last_success_at=connection.last_success_at,
            last_failure_at=timestamp,
            updated_at=timestamp,
        )
        self._connections[connection_id] = updated
        return updated

    def _validate_actor_scope(
        self,
        connection: ConnectionDefinition,
        actor_scope: ActorScope,
    ) -> None:
        if connection.owner_tenant_id != actor_scope.tenant_id:
            raise ValueError(IntegrationErrorCode.TENANT_SCOPE_VIOLATION)
        if (
            connection.owner_user_id is not None
            and connection.owner_user_id != actor_scope.user_id
        ):
            raise ValueError(IntegrationErrorCode.USER_SCOPE_VIOLATION)


class InMemoryCapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, IntegrationCapability] = {}

    def register(self, capability: IntegrationCapability) -> None:
        if capability.capability_id in self._capabilities:
            raise ValueError(f"duplicate capability_id: {capability.capability_id}")
        self._capabilities[capability.capability_id] = capability

    def get(self, capability_id: str) -> IntegrationCapability | None:
        return self._capabilities.get(capability_id)

    def list_by_integration(self, integration_id: str) -> list[IntegrationCapability]:
        return sorted(
            (
                capability
                for capability in self._capabilities.values()
                if capability.integration_id == integration_id
            ),
            key=lambda item: item.capability_id,
        )

    def list_all(self) -> list[IntegrationCapability]:
        return sorted(self._capabilities.values(), key=lambda item: item.capability_id)


class EnvironmentCredentialResolver:
    def resolve(
        self,
        credential_ref: CredentialReference,
        *,
        actor_scope: ActorScope,
    ) -> ResolvedCredential:
        if credential_ref.tenant_id != actor_scope.tenant_id:
            raise IntegrationCredentialError(
                IntegrationErrorCode.TENANT_SCOPE_VIOLATION,
                "Credential tenant scope does not match request actor.",
            )
        if (
            credential_ref.user_id is not None
            and credential_ref.user_id != actor_scope.user_id
        ):
            raise IntegrationCredentialError(
                IntegrationErrorCode.USER_SCOPE_VIOLATION,
                "Credential user scope does not match request actor.",
            )
        if (
            actor_scope.environment != "default"
            and credential_ref.environment != actor_scope.environment
        ):
            raise IntegrationCredentialError(
                IntegrationErrorCode.CONFIGURATION_ERROR,
                "Credential environment does not match request actor.",
            )
        value = self._resolve_value(credential_ref)
        if not value:
            raise IntegrationCredentialError(
                IntegrationErrorCode.MISSING_CREDENTIALS,
                "Credential is not configured for this connection.",
            )
        return ResolvedCredential(
            credential_ref_id=credential_ref.credential_ref_id,
            integration_id=credential_ref.integration_id,
            source=credential_ref.source,
            value=value,
            safe_metadata=credential_ref.safe_metadata,
        )

    def _resolve_value(self, credential_ref: CredentialReference) -> str | None:
        if credential_ref.source == "env":
            return os.getenv(credential_ref.key)
        if credential_ref.source == "json_file_field":
            try:
                with open(credential_ref.key, encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, json.JSONDecodeError):
                return None
            field = str(credential_ref.safe_metadata.get("field") or "access_token")
            value = payload.get(field) if isinstance(payload, Mapping) else None
            return str(value) if value else None
        raise IntegrationCredentialError(
            IntegrationErrorCode.CONFIGURATION_ERROR,
            "Unsupported credential source.",
        )


class IntegrationAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, IntegrationAdapter] = {}

    def register(self, adapter: IntegrationAdapter) -> None:
        adapter_id = adapter.metadata.adapter_id
        if adapter_id in self._adapters:
            raise ValueError(f"duplicate adapter_id: {adapter_id}")
        self._adapters[adapter_id] = adapter

    def get(self, adapter_id: str) -> IntegrationAdapter | None:
        return self._adapters.get(adapter_id)

    def list_all(self) -> list[IntegrationAdapterMetadata]:
        return sorted(
            (adapter.metadata for adapter in self._adapters.values()),
            key=lambda item: item.adapter_id,
        )


class IntegrationService:
    def __init__(
        self,
        *,
        connection_registry: ConnectionRegistry,
        capability_registry: InMemoryCapabilityRegistry,
        adapter_registry: IntegrationAdapterRegistry,
        credential_resolver: EnvironmentCredentialResolver,
    ) -> None:
        self.connection_registry = connection_registry
        self.capability_registry = capability_registry
        self.adapter_registry = adapter_registry
        self.credential_resolver = credential_resolver

    def execute_read(self, request: IntegrationRequest) -> IntegrationResult:
        started = time.monotonic()
        capability = self.capability_registry.get(request.capability_id)
        if capability is None:
            return self._failure(
                request=request,
                capability=None,
                connection=None,
                code=IntegrationErrorCode.UNSUPPORTED_OPERATION,
                safe_summary="Capability is not registered.",
                started=started,
            )
        if not capability.enabled or capability.lifecycle_state != "active":
            return self._failure(
                request=request,
                capability=capability,
                connection=None,
                code=IntegrationErrorCode.DISABLED,
                safe_summary="Capability is disabled.",
                started=started,
            )
        if capability.read_write != "read":
            return self._failure(
                request=request,
                capability=capability,
                connection=None,
                code=IntegrationErrorCode.UNSUPPORTED_OPERATION,
                safe_summary="Only read capabilities are available through execute_read.",
                started=started,
            )
        connection = self._resolve_connection(request, capability, started)
        if isinstance(connection, IntegrationResult):
            return connection
        if not connection.enabled or connection.status != IntegrationState.CONNECTED:
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.DISABLED,
                safe_summary=f"Connection is not connected ({connection.status}).",
                started=started,
            )
        missing_scopes = sorted(
            set(capability.required_scopes) - set(connection.scopes)
        )
        if missing_scopes:
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.INSUFFICIENT_SCOPE,
                safe_summary="Connection does not include the required read scope.",
                started=started,
            )
        credential: ResolvedCredential | None = None
        try:
            if connection.credential_ref is None:
                raise IntegrationCredentialError(
                    IntegrationErrorCode.MISSING_CREDENTIALS,
                    "Connection has no credential reference.",
                )
            credential = self.credential_resolver.resolve(
                connection.credential_ref,
                actor_scope=request.actor_scope,
            )
        except IntegrationCredentialError as exc:
            self.connection_registry.record_failure(
                connection.connection_id,
                reason_code=exc.code,
                safe_summary=exc.safe_summary,
                latency_ms=self._latency(started),
                actor_scope=request.actor_scope,
            )
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=exc.code,
                safe_summary=exc.safe_summary,
                started=started,
            )
        adapter = self.adapter_registry.get(capability.adapter_id)
        if (
            adapter is None
            or request.capability_id not in adapter.metadata.supported_capability_ids
        ):
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.UNSUPPORTED_OPERATION,
                safe_summary="No adapter supports this capability.",
                started=started,
                credential_resolved=credential is not None,
            )
        try:
            data = adapter.execute_read(request, connection, credential)
        except TimeoutError:
            self.connection_registry.record_failure(
                connection.connection_id,
                reason_code=IntegrationErrorCode.TIMEOUT,
                safe_summary="Adapter read timed out.",
                latency_ms=self._latency(started),
                actor_scope=request.actor_scope,
            )
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.TIMEOUT,
                safe_summary="Adapter read timed out.",
                started=started,
                retryable=True,
                credential_resolved=True,
            )
        except Exception:
            self.connection_registry.record_failure(
                connection.connection_id,
                reason_code=IntegrationErrorCode.UNKNOWN_FAILURE,
                safe_summary="Adapter read failed.",
                latency_ms=self._latency(started),
                actor_scope=request.actor_scope,
            )
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.UNKNOWN_FAILURE,
                safe_summary="Adapter read failed.",
                started=started,
                retryable=True,
                credential_resolved=True,
            )
        latency = self._latency(started)
        updated_connection = self.connection_registry.record_success(
            connection.connection_id,
            latency_ms=latency,
            actor_scope=request.actor_scope,
        )
        return IntegrationResult(
            status="ok",
            data=data,
            error=None,
            integration_id=capability.integration_id,
            connection_id=updated_connection.connection_id,
            capability_id=capability.capability_id,
            adapter_id=capability.adapter_id,
            connection_state=updated_connection.status,
            health_state=updated_connection.health.status,
            latency_ms=latency,
            retry_count=0,
            credential_resolved=True,
            audit_metadata=self._audit_metadata(request),
            trace_metadata={
                "connection": updated_connection.safe_trace(),
                "capability": capability.safe_trace(),
            },
        )

    def _resolve_connection(
        self,
        request: IntegrationRequest,
        capability: IntegrationCapability,
        started: float,
    ) -> ConnectionDefinition | IntegrationResult:
        connection: ConnectionDefinition | None
        try:
            if request.connection_id:
                connection = self.connection_registry.get(
                    request.connection_id,
                    actor_scope=request.actor_scope,
                )
            else:
                connection = self.connection_registry.find_eligible_connection(
                    integration_id=capability.integration_id,
                    actor_scope=request.actor_scope,
                    capability_id=capability.capability_id,
                )
                if connection is None:
                    return self._failure(
                        request=request,
                        capability=capability,
                        connection=None,
                        code=IntegrationErrorCode.CONFIGURATION_ERROR,
                        safe_summary="No scoped connection is available for this capability.",
                        started=started,
                    )
        except KeyError:
            return self._failure(
                request=request,
                capability=capability,
                connection=None,
                code=IntegrationErrorCode.CONFIGURATION_ERROR,
                safe_summary="Connection is not registered.",
                started=started,
            )
        except ValueError as exc:
            code = str(exc) or IntegrationErrorCode.UNKNOWN_FAILURE
            if code not in {
                IntegrationErrorCode.TENANT_SCOPE_VIOLATION,
                IntegrationErrorCode.USER_SCOPE_VIOLATION,
            }:
                code = IntegrationErrorCode.UNKNOWN_FAILURE
            return self._failure(
                request=request,
                capability=capability,
                connection=None,
                code=code,
                safe_summary="Connection scope does not match request actor.",
                started=started,
            )
        if capability.capability_id not in connection.capability_ids:
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.UNSUPPORTED_OPERATION,
                safe_summary="Connection is not authorised for this capability.",
                started=started,
            )
        if (
            request.actor_scope.environment != "default"
            and connection.environment != request.actor_scope.environment
        ):
            return self._failure(
                request=request,
                capability=capability,
                connection=connection,
                code=IntegrationErrorCode.CONFIGURATION_ERROR,
                safe_summary="Connection environment does not match request actor.",
                started=started,
            )
        return connection

    def _failure(
        self,
        *,
        request: IntegrationRequest,
        capability: IntegrationCapability | None,
        connection: ConnectionDefinition | None,
        code: str,
        safe_summary: str,
        started: float,
        retryable: bool = False,
        upstream_status: int | None = None,
        credential_resolved: bool = False,
    ) -> IntegrationResult:
        error = IntegrationError(
            code=code,
            safe_summary=safe_summary,
            retryable=retryable,
            upstream_status=upstream_status,
        )
        return IntegrationResult(
            status="failed",
            data={},
            error=error,
            integration_id=capability.integration_id if capability else None,
            connection_id=connection.connection_id
            if connection
            else request.connection_id,
            capability_id=request.capability_id,
            adapter_id=capability.adapter_id if capability else None,
            connection_state=connection.status if connection else None,
            health_state=connection.health.status if connection else "unknown",
            latency_ms=self._latency(started),
            retry_count=0,
            credential_resolved=credential_resolved,
            audit_metadata=self._audit_metadata(request),
            trace_metadata={
                "connection": connection.safe_trace() if connection else None,
                "capability": capability.safe_trace() if capability else None,
            },
        )

    def _audit_metadata(self, request: IntegrationRequest) -> dict[str, Any]:
        return _redact({
            "actor_scope": {
                "tenant_id": request.actor_scope.tenant_id,
                "user_scoped": request.actor_scope.user_id is not None,
                "environment": request.actor_scope.environment,
            },
            "request_id": request.request_id,
            "trace_context": request.trace_context,
        })

    def _latency(self, started: float) -> float:
        return round((time.monotonic() - started) * 1000, 3)
