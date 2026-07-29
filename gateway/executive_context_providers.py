"""Executive context provider framework for Hermes.

The framework is deliberately local and declarative. Providers contribute
bounded context records with provenance; this module does not invoke external
connectors, MCP servers, adapters, subprocesses, or network clients.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import os
import re
import time
from typing import TYPE_CHECKING, Any, Mapping, Protocol

from utils import is_truthy_value

if TYPE_CHECKING:
    from gateway.executive_orchestrator import (
        ContextItem,
        ExecutiveContextLimits,
        ExecutiveTurnInput,
    )


_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*=\s*\S+"),
    re.compile(r"(?i)(bearer)\s+[A-Za-z0-9._-]+"),
)


def _redact_secrets(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _safe_label(value: str | None) -> str:
    return _redact_secrets(str(value or "unknown"))[:160]


def _normalize_message(message: Any) -> str:
    if isinstance(message, str):
        return " ".join(message.split())
    return " ".join(str(message).split())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _require_nonempty(field_name: str, value: str) -> None:
    if not str(value or "").strip():
        raise ValueError(f"{field_name} is required")


@dataclass(frozen=True)
class ContextEvidenceReference:
    evidence_id: str
    source_provider_id: str
    source_mechanism: str
    source_record_ref: str
    observed_at: str
    digest: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty("evidence_id", self.evidence_id)
        _require_nonempty("source_provider_id", self.source_provider_id)
        _require_nonempty("source_mechanism", self.source_mechanism)
        _require_nonempty("source_record_ref", self.source_record_ref)
        _require_nonempty("observed_at", self.observed_at)

    def safe_trace(self) -> dict[str, str | None]:
        return {
            "evidence_id": _safe_label(self.evidence_id),
            "source_provider_id": _safe_label(self.source_provider_id),
            "source_mechanism": _safe_label(self.source_mechanism),
            "source_record_ref": _safe_label(self.source_record_ref),
            "observed_at": _safe_label(self.observed_at),
            "digest": _safe_label(self.digest) if self.digest else None,
        }


@dataclass(frozen=True)
class ExecutiveContextContribution:
    contribution_id: str
    context_type: str
    title: str
    summary: str
    payload: Mapping[str, Any]
    source_provider_id: str
    source_mechanism: str
    source_record_ref: str
    observed_at: str
    confidence: float = 1.0
    freshness_state: str = "current"
    sensitivity: str = "internal"
    tenant_id: str | None = None
    user_id: str | None = None
    evidence_refs: tuple[ContextEvidenceReference, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_nonempty("contribution_id", self.contribution_id)
        _require_nonempty("context_type", self.context_type)
        _require_nonempty("source_provider_id", self.source_provider_id)
        _require_nonempty("source_mechanism", self.source_mechanism)
        _require_nonempty("source_record_ref", self.source_record_ref)
        _require_nonempty("observed_at", self.observed_at)
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    def validate_scope(self, *, tenant_id: str, user_id: str | None = None) -> None:
        if self.tenant_id is not None and self.tenant_id != tenant_id:
            raise ValueError("tenant scope mismatch")
        if user_id and self.user_id is not None and self.user_id != user_id:
            raise ValueError("user scope mismatch")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "contribution_id": _safe_label(self.contribution_id),
            "context_type": _safe_label(self.context_type),
            "source_provider_id": _safe_label(self.source_provider_id),
            "source_mechanism": _safe_label(self.source_mechanism),
            "source_record_ref": _safe_label(self.source_record_ref),
            "observed_at": _safe_label(self.observed_at),
            "confidence": round(float(self.confidence), 3),
            "freshness_state": _safe_label(self.freshness_state),
            "sensitivity": _safe_label(self.sensitivity),
            "tenant_id_digest": _digest(self.tenant_id or "")[:16]
            if self.tenant_id
            else None,
            "user_id_digest": _digest(self.user_id or "")[:16]
            if self.user_id
            else None,
            "evidence_ids": [ref.evidence_id for ref in self.evidence_refs],
            "tags": [_safe_label(tag) for tag in self.tags],
        }

    def to_context_item(self) -> ContextItem:
        from gateway.executive_orchestrator import ContextItem

        trace_category = str(
            self.payload.get("trace_category") or self.context_type
        ).strip()
        return ContextItem(
            source=_safe_label(trace_category),
            reference_id=_safe_label(self.source_record_ref),
            title=_safe_label(self.title),
            summary=_redact_secrets(str(self.summary)),
        )


@dataclass(frozen=True)
class ExecutiveContextProviderMetadata:
    provider_id: str
    version: str
    provider_type: str
    supported_context_types: tuple[str, ...]
    source_mechanism: str
    enabled: bool = True
    deterministic: bool = True
    uses_external_data: bool = False
    timeout_ms: int = 250
    sensitivity: str = "internal"
    health_state: str = "healthy"

    def __post_init__(self) -> None:
        _require_nonempty("provider_id", self.provider_id)
        _require_nonempty("version", self.version)
        _require_nonempty("provider_type", self.provider_type)
        _require_nonempty("source_mechanism", self.source_mechanism)
        if not self.supported_context_types:
            raise ValueError("supported_context_types must not be empty")


@dataclass(frozen=True)
class ExecutiveContextProviderRequest:
    turn: ExecutiveTurnInput
    request_classification: str
    required_context_types: tuple[str, ...]
    limits: ExecutiveContextLimits
    conversation_history: tuple[Mapping[str, Any], ...] = ()
    agent: Any = None


class ExecutiveContextProvider(Protocol):
    metadata: ExecutiveContextProviderMetadata

    def collect(
        self,
        request: ExecutiveContextProviderRequest,
    ) -> tuple[ExecutiveContextContribution, ...]: ...


@dataclass(frozen=True)
class ExecutiveContextSnapshot:
    tenant_id: str
    user_id: str
    request_classification: str
    contributions: tuple[ExecutiveContextContribution, ...]
    selected_provider_ids: tuple[str, ...]
    successful_provider_ids: tuple[str, ...]
    failed_provider_ids: tuple[str, ...]
    provider_trace: Mapping[str, Mapping[str, Any]]
    warnings: tuple[str, ...]
    total_collection_latency_ms: int
    composed_context: str
    context_digest: str
    snapshot_digest: str

    @property
    def contribution_counts_by_type(self) -> Mapping[str, int]:
        return dict(Counter(item.context_type for item in self.contributions))

    def to_context_items(self) -> Mapping[str, tuple[ContextItem, ...]]:
        grouped: dict[str, list[ContextItem]] = {}
        for contribution in self.contributions:
            item = contribution.to_context_item()
            grouped.setdefault(item.source, []).append(item)
        return {key: tuple(value) for key, value in grouped.items()}

    def safe_trace_metadata(self) -> dict[str, Any]:
        return {
            "tenant_id_digest": _digest(self.tenant_id)[:16],
            "user_id_digest": _digest(self.user_id)[:16] if self.user_id else None,
            "request_classification": _safe_label(self.request_classification),
            "selected_provider_ids": list(self.selected_provider_ids),
            "successful_provider_ids": list(self.successful_provider_ids),
            "failed_provider_ids": list(self.failed_provider_ids),
            "contribution_counts_by_type": dict(self.contribution_counts_by_type),
            "provider_trace": {
                provider_id: dict(trace)
                for provider_id, trace in sorted(self.provider_trace.items())
            },
            "warnings": list(self.warnings),
            "total_collection_latency_ms": self.total_collection_latency_ms,
            "context_digest": self.context_digest,
            "snapshot_digest": self.snapshot_digest,
        }


class ExecutiveContextProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ExecutiveContextProvider] = {}
        self._enabled_overrides: dict[str, bool] = {}

    def register(self, provider: ExecutiveContextProvider) -> None:
        provider_id = provider.metadata.provider_id
        if provider_id in self._providers:
            raise ValueError(f"duplicate executive context provider: {provider_id}")
        self._providers[provider_id] = provider

    def lookup(self, provider_id: str) -> ExecutiveContextProvider | None:
        return self._providers.get(provider_id)

    def set_enabled(self, provider_id: str, enabled: bool) -> None:
        if provider_id not in self._providers:
            raise KeyError(provider_id)
        self._enabled_overrides[provider_id] = enabled

    def providers_for_context_type(
        self,
        context_type: str,
    ) -> tuple[ExecutiveContextProvider, ...]:
        providers = [
            provider
            for provider in self._providers.values()
            if context_type in provider.metadata.supported_context_types
            and self._provider_enabled(provider)
        ]
        return tuple(sorted(providers, key=lambda item: item.metadata.provider_id))

    def health(self) -> dict[str, dict[str, Any]]:
        return {
            provider_id: {
                "enabled": self._provider_enabled(provider),
                "provider_type": provider.metadata.provider_type,
                "health_state": provider.metadata.health_state,
                "uses_external_data": provider.metadata.uses_external_data,
                "supported_context_types": list(
                    provider.metadata.supported_context_types
                ),
            }
            for provider_id, provider in sorted(self._providers.items())
        }

    def _provider_enabled(self, provider: ExecutiveContextProvider) -> bool:
        override = self._enabled_overrides.get(provider.metadata.provider_id)
        return provider.metadata.enabled if override is None else override


class ExecutiveContextCollectionService:
    def __init__(self, *, registry: ExecutiveContextProviderRegistry) -> None:
        self.registry = registry

    def collect(
        self,
        *,
        turn: ExecutiveTurnInput,
        request_classification: str,
        limits: ExecutiveContextLimits,
        conversation_history: list[Mapping[str, Any]]
        | tuple[Mapping[str, Any], ...] = (),
        agent: Any = None,
    ) -> ExecutiveContextSnapshot:
        started = time.monotonic()
        required = required_context_types_for_classification(
            request_classification,
            message=str(turn.message or ""),
        )
        selected = self._select_providers(
            required, turn=turn, classification=request_classification
        )
        request = ExecutiveContextProviderRequest(
            turn=turn,
            request_classification=request_classification,
            required_context_types=required,
            limits=limits,
            conversation_history=tuple(conversation_history),
            agent=agent,
        )
        contributions: list[ExecutiveContextContribution] = []
        seen: set[str] = set()
        successful: list[str] = []
        failed: list[str] = []
        warnings: list[str] = []
        provider_trace: dict[str, Mapping[str, Any]] = {}
        budget_remaining = max(0, int(limits.max_context_chars))
        user_id = str(turn.actor_id or "")

        for provider in selected:
            provider_id = provider.metadata.provider_id
            provider_started = time.monotonic()
            try:
                provider_contributions = tuple(provider.collect(request))
                latency_ms = int((time.monotonic() - provider_started) * 1000)
                if latency_ms > provider.metadata.timeout_ms:
                    failed.append(provider_id)
                    warnings.append(f"provider_timeout:{provider_id}")
                    provider_trace[provider_id] = {
                        "status": "timeout",
                        "latency_ms": latency_ms,
                        "timeout_ms": provider.metadata.timeout_ms,
                    }
                    continue
            except Exception as exc:
                failed.append(provider_id)
                warnings.append(f"provider_failed:{provider_id}")
                provider_trace[provider_id] = {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                }
                continue

            accepted_for_provider = 0
            for contribution in provider_contributions:
                try:
                    contribution.validate_scope(
                        tenant_id=turn.tenant_id, user_id=user_id
                    )
                except ValueError:
                    warnings.append(
                        f"scope_rejected:{provider_id}:{contribution.contribution_id}"
                    )
                    continue
                if contribution.contribution_id in seen:
                    warnings.append(
                        f"duplicate_contribution:{provider_id}:{contribution.contribution_id}"
                    )
                    continue
                rendered = _render_contribution(contribution)
                if len(rendered) > budget_remaining:
                    warnings.append(
                        f"context_budget_exhausted:{provider_id}:{contribution.contribution_id}"
                    )
                    continue
                budget_remaining -= len(rendered)
                seen.add(contribution.contribution_id)
                contributions.append(contribution)
                accepted_for_provider += 1
            successful.append(provider_id)
            provider_trace[provider_id] = {
                "status": "ok",
                "latency_ms": int((time.monotonic() - provider_started) * 1000),
                "accepted_contributions": accepted_for_provider,
                "supported_context_types": list(
                    provider.metadata.supported_context_types
                ),
                "provider_type": provider.metadata.provider_type,
                "uses_external_data": provider.metadata.uses_external_data,
            }

        composed_context = _compose_context(
            contributions, max_chars=limits.max_context_chars
        )
        context_digest = f"context_{_digest(composed_context)[:16]}"
        snapshot_seed = {
            "tenant": _digest(turn.tenant_id)[:16],
            "user": _digest(user_id)[:16],
            "classification": request_classification,
            "contributions": [item.safe_trace() for item in contributions],
            "warnings": warnings,
        }
        return ExecutiveContextSnapshot(
            tenant_id=turn.tenant_id,
            user_id=user_id,
            request_classification=request_classification,
            contributions=tuple(contributions),
            selected_provider_ids=tuple(
                provider.metadata.provider_id for provider in selected
            ),
            successful_provider_ids=tuple(successful),
            failed_provider_ids=tuple(failed),
            provider_trace=provider_trace,
            warnings=tuple(warnings),
            total_collection_latency_ms=int((time.monotonic() - started) * 1000),
            composed_context=composed_context,
            context_digest=context_digest,
            snapshot_digest=f"snapshot_{_digest(json.dumps(snapshot_seed, sort_keys=True))[:16]}",
        )

    def _select_providers(
        self,
        required_context_types: tuple[str, ...],
        *,
        turn: ExecutiveTurnInput,
        classification: str,
    ) -> tuple[ExecutiveContextProvider, ...]:
        selected: dict[str, ExecutiveContextProvider] = {}
        for context_type in required_context_types:
            for provider in self.registry.providers_for_context_type(context_type):
                if (
                    provider.metadata.provider_id == "mock_executive_context"
                    and not is_executive_context_mock_provider_enabled()
                ):
                    continue
                if (
                    provider.metadata.provider_type == "mcp"
                    and not is_mcp_context_adapter_enabled()
                ):
                    continue
                if provider.metadata.provider_id == "google_calendar_context":
                    from gateway.google_calendar_context_provider import (
                        should_select_google_calendar_context,
                    )

                    if not should_select_google_calendar_context(
                        str(turn.message or ""), classification
                    ):
                        continue
                selected[provider.metadata.provider_id] = provider
        return tuple(
            sorted(selected.values(), key=lambda item: item.metadata.provider_id)
        )


class CurrentRequestMetadataProvider:
    metadata = ExecutiveContextProviderMetadata(
        provider_id="current_request_metadata",
        version="1.0.0",
        provider_type="internal",
        supported_context_types=("capability_status",),
        source_mechanism="runtime_request_metadata",
        sensitivity="internal",
    )

    def collect(
        self,
        request: ExecutiveContextProviderRequest,
    ) -> tuple[ExecutiveContextContribution, ...]:
        turn = request.turn
        normalized = _normalize_message(turn.message)
        ref = f"current_request:{_digest(normalized)[:12]}"
        return (
            ExecutiveContextContribution(
                contribution_id=ref,
                context_type="capability_status",
                title="Current request metadata",
                summary=(
                    f"platform={_safe_label(turn.platform)} "
                    f"actor_digest={_digest(turn.actor_id)[:12]} "
                    f"message_digest={_digest(normalized)[:16]} "
                    "execution_boundary=not_executed"
                ),
                payload={"trace_category": "current_request_metadata"},
                source_provider_id=self.metadata.provider_id,
                source_mechanism=self.metadata.source_mechanism,
                source_record_ref=ref,
                observed_at=_now_iso(),
                tenant_id=turn.tenant_id,
                user_id=turn.actor_id,
                evidence_refs=(
                    ContextEvidenceReference(
                        evidence_id=ref,
                        source_provider_id=self.metadata.provider_id,
                        source_mechanism=self.metadata.source_mechanism,
                        source_record_ref=ref,
                        observed_at=_now_iso(),
                        digest=_digest(normalized)[:16],
                    ),
                ),
                tags=("request_metadata", "no_execution"),
            ),
        )


class RecentConversationProvider:
    def __init__(self, *, max_messages: int = 6) -> None:
        self.max_messages = max_messages
        self.metadata = ExecutiveContextProviderMetadata(
            provider_id="recent_conversation",
            version="1.0.0",
            provider_type="internal",
            supported_context_types=("message",),
            source_mechanism="runtime_conversation_history",
            sensitivity="private",
        )

    def collect(
        self,
        request: ExecutiveContextProviderRequest,
    ) -> tuple[ExecutiveContextContribution, ...]:
        history = [
            item for item in request.conversation_history if isinstance(item, Mapping)
        ]
        selected = history[-self.max_messages :]
        offset = max(0, len(history) - len(selected))
        contributions: list[ExecutiveContextContribution] = []
        for relative_index, entry in enumerate(selected):
            absolute_index = offset + relative_index
            content = _normalize_message(entry.get("content") or "")
            role = _safe_label(str(entry.get("role") or "unknown"))
            ref = f"recent_conversation:{absolute_index}:{_digest(content)[:12]}"
            contributions.append(
                ExecutiveContextContribution(
                    contribution_id=ref,
                    context_type="message",
                    title="Recent conversation turn",
                    summary=f"role={role} content_digest={_digest(content)[:16]}",
                    payload={"trace_category": "recent_conversation"},
                    source_provider_id=self.metadata.provider_id,
                    source_mechanism=self.metadata.source_mechanism,
                    source_record_ref=ref,
                    observed_at=_now_iso(),
                    tenant_id=request.turn.tenant_id,
                    user_id=request.turn.actor_id,
                    evidence_refs=(
                        ContextEvidenceReference(
                            evidence_id=ref,
                            source_provider_id=self.metadata.provider_id,
                            source_mechanism=self.metadata.source_mechanism,
                            source_record_ref=ref,
                            observed_at=_now_iso(),
                            digest=_digest(content)[:16],
                        ),
                    ),
                    tags=("recent_conversation",),
                )
            )
        return tuple(contributions)


class PersistentProfileProvider:
    metadata = ExecutiveContextProviderMetadata(
        provider_id="persistent_profile",
        version="1.0.0",
        provider_type="internal",
        supported_context_types=("identity",),
        source_mechanism="internal_memory",
        sensitivity="private",
    )

    def collect(
        self,
        request: ExecutiveContextProviderRequest,
    ) -> tuple[ExecutiveContextContribution, ...]:
        agent = request.agent
        if not (
            getattr(agent, "_memory_enabled", False)
            or getattr(agent, "_user_profile_enabled", False)
            or getattr(agent, "_memory_store", None) is not None
        ):
            return ()
        enabled_parts: list[str] = []
        if getattr(agent, "_memory_enabled", False):
            enabled_parts.append("memory")
        if getattr(agent, "_user_profile_enabled", False):
            enabled_parts.append("user_profile")
        if not enabled_parts:
            enabled_parts.append("persistent_context")
        ref = f"persistent_profile:{_digest('|'.join(enabled_parts))[:12]}"
        return (
            ExecutiveContextContribution(
                contribution_id=ref,
                context_type="identity",
                title="Persistent profile context",
                summary=(
                    "Persistent profile or memory context is available to the reasoning "
                    "provider; raw profile content is not included in trace metadata."
                ),
                payload={"trace_category": "persistent_profile"},
                source_provider_id=self.metadata.provider_id,
                source_mechanism=self.metadata.source_mechanism,
                source_record_ref=ref,
                observed_at=_now_iso(),
                tenant_id=request.turn.tenant_id,
                user_id=request.turn.actor_id,
                evidence_refs=(
                    ContextEvidenceReference(
                        evidence_id=ref,
                        source_provider_id=self.metadata.provider_id,
                        source_mechanism=self.metadata.source_mechanism,
                        source_record_ref=ref,
                        observed_at=_now_iso(),
                        digest=_digest("|".join(enabled_parts))[:16],
                    ),
                ),
                tags=("persistent_profile",),
            ),
        )


class MockExecutiveContextProvider:
    metadata = ExecutiveContextProviderMetadata(
        provider_id="mock_executive_context",
        version="1.0.0",
        provider_type="synthetic",
        supported_context_types=(
            "active_project",
            "commitment",
            "priority",
            "risk",
        ),
        source_mechanism="synthetic_test_fixture",
        sensitivity="internal",
    )

    def collect(
        self,
        request: ExecutiveContextProviderRequest,
    ) -> tuple[ExecutiveContextContribution, ...]:
        if not is_executive_context_mock_provider_enabled():
            return ()
        records = (
            ("active_project", "Hermes behavioural validation"),
            ("priority", "Keep executive behaviour stable before connectors"),
            ("risk", "Do not enable live execution before the controlled boundary"),
            ("commitment", "Preserve no-execution safety while improving context"),
        )
        return tuple(
            self._record(request, context_type=context_type, summary=summary)
            for context_type, summary in records
        )

    def _record(
        self,
        request: ExecutiveContextProviderRequest,
        *,
        context_type: str,
        summary: str,
    ) -> ExecutiveContextContribution:
        ref = f"mock:{context_type}:{_digest(summary)[:12]}"
        return ExecutiveContextContribution(
            contribution_id=ref,
            context_type=context_type,
            title=f"Synthetic {context_type.replace('_', ' ')}",
            summary=summary,
            payload={"trace_category": context_type},
            source_provider_id=self.metadata.provider_id,
            source_mechanism=self.metadata.source_mechanism,
            source_record_ref=ref,
            observed_at=_now_iso(),
            tenant_id=request.turn.tenant_id,
            user_id=request.turn.actor_id,
            evidence_refs=(
                ContextEvidenceReference(
                    evidence_id=ref,
                    source_provider_id=self.metadata.provider_id,
                    source_mechanism=self.metadata.source_mechanism,
                    source_record_ref=ref,
                    observed_at=_now_iso(),
                    digest=_digest(summary)[:16],
                ),
            ),
            tags=("mock", context_type),
        )


class MCPContextProviderBoundary:
    """Fail-closed boundary for future read-only MCP context providers."""

    metadata = ExecutiveContextProviderMetadata(
        provider_id="mcp_context_boundary",
        version="1.0.0",
        provider_type="mcp",
        supported_context_types=("external_context",),
        source_mechanism="mcp_read_only_boundary",
        enabled=False,
        deterministic=False,
        uses_external_data=True,
        health_state="disabled",
    )

    def collect_resource(
        self,
        *,
        server_id: str,
        resource_id: str,
        tenant_id: str,
        user_id: str,
    ) -> tuple[ExecutiveContextContribution, ...]:
        del server_id, resource_id, tenant_id, user_id
        if not is_mcp_context_adapter_enabled():
            raise RuntimeError("MCP context adapter disabled")
        raise RuntimeError("MCP read-only context adapter has no authorised connector")


def build_default_context_provider_registry() -> ExecutiveContextProviderRegistry:
    from gateway.google_calendar_context_provider import GoogleCalendarContextProvider

    registry = ExecutiveContextProviderRegistry()
    registry.register(CurrentRequestMetadataProvider())
    registry.register(PersistentProfileProvider())
    registry.register(RecentConversationProvider())
    registry.register(GoogleCalendarContextProvider())
    registry.register(MockExecutiveContextProvider())
    return registry


def build_default_context_collection_service() -> ExecutiveContextCollectionService:
    return ExecutiveContextCollectionService(
        registry=build_default_context_provider_registry()
    )


def is_executive_context_provider_framework_enabled() -> bool:
    value = os.getenv("HERMES_EXECUTIVE_CONTEXT_PROVIDER_FRAMEWORK_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_executive_context_mock_provider_enabled() -> bool:
    return is_truthy_value(os.getenv("HERMES_EXECUTIVE_CONTEXT_MOCK_PROVIDER_ENABLED"))


def is_mcp_context_adapter_enabled() -> bool:
    return is_truthy_value(os.getenv("HERMES_MCP_CONTEXT_ADAPTER_ENABLED"))


def classify_mcp_tool_access(tool_schema: Mapping[str, Any]) -> str:
    if bool(tool_schema.get("readOnlyHint")):
        return "read"
    name = str(tool_schema.get("name") or tool_schema.get("id") or "").casefold()
    normalised_name = re.sub(r"[^a-z0-9]+", " ", name)
    if re.search(
        r"\b(create|update|delete|send|schedule|write|modify|patch)\b",
        normalised_name,
    ):
        return "write"
    if re.search(r"\b(get|list|search|read|fetch|query)\b", normalised_name):
        return "read"
    return "unknown"


def required_context_types_for_classification(
    request_classification: str,
    message: str | None = None,
) -> tuple[str, ...]:
    common = ("capability_status",)
    mapping = {
        "ordinary_conversation": ("identity", "message", *common),
        "executive_status": (
            "identity",
            "message",
            "active_project",
            "priority",
            "commitment",
            "risk",
            "opportunity",
            "decision",
            "approval",
            "execution_request",
            "daily_brief_item",
            *common,
        ),
        "decision_support": (
            "identity",
            "message",
            "active_project",
            "priority",
            "risk",
            "opportunity",
            "decision",
            "commitment",
            *common,
        ),
        "planning_request": (
            "identity",
            "message",
            "active_project",
            "priority",
            "risk",
            "decision",
            "commitment",
            *common,
        ),
        "daily_brief": ("identity", "message", "daily_brief_item", *common),
        "approval_related": ("approval", "decision", "execution_request", *common),
        "deterministic_ovos_command": ("message", "deterministic_output", *common),
        "unsupported_or_unsafe": common,
        "potentially_executable": common,
    }
    required = list(mapping.get(request_classification, common))
    if message is not None:
        from gateway.google_calendar_context_provider import (
            should_select_google_calendar_context,
        )

        if should_select_google_calendar_context(message, request_classification):
            required.extend([
                "calendar_capability_status",
                "schedule_summary",
                "meeting",
                "availability",
                "calendar_conflict",
                "preparation_requirement",
            ])
    return tuple(dict.fromkeys(required))


def _compose_context(
    contributions: tuple[ExecutiveContextContribution, ...]
    | list[ExecutiveContextContribution],
    *,
    max_chars: int,
) -> str:
    if not contributions:
        return "No executive context provider contributions were available."
    lines = ["Executive context provider snapshot:"]
    for item in sorted(contributions, key=lambda value: value.contribution_id):
        lines.append(
            f"- [{item.source_record_ref}] {item.context_type}: "
            f"{_redact_secrets(item.summary)}"
        )
    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 30)].rstrip() + "\n[context truncated]"


def _render_contribution(item: ExecutiveContextContribution) -> str:
    return (
        f"[{item.source_record_ref}] {item.context_type}: "
        f"{_redact_secrets(item.title)} {_redact_secrets(item.summary)}"
    )
