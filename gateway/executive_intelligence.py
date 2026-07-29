"""Deterministic Executive Intelligence Engine for Hermes.

This layer consumes Hermes-owned executive context contributions and derives
bounded, evidence-backed signals. It does not call integrations, credentials,
MCP, LLMs, subprocesses, or external execution interfaces.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, time as dt_time, timedelta
import hashlib
import json
import os
import time
from typing import Any, Protocol

from gateway.executive_context_providers import (
    ContextEvidenceReference,
    ExecutiveContextContribution,
    ExecutiveContextSnapshot,
)
from utils import is_truthy_value


SEVERITIES = ("informational", "low", "medium", "high", "critical")
PRIORITIES = ("background", "normal", "attention", "urgent")
FRESHNESS_STATES = ("current", "stale", "expired", "unknown")
FACT_OR_INFERENCE = (
    "source_fact",
    "derived_fact",
    "deterministic_signal",
    "inference",
)


class IntelligenceErrorCode:
    UNKNOWN_MODULE = "unknown_module"
    MODULE_EXCEPTION = "module_exception"
    MODULE_TIMEOUT = "module_timeout"
    INVALID_OUTPUT = "invalid_output"
    MISSING_EVIDENCE = "missing_evidence"
    TENANT_SCOPE_VIOLATION = "tenant_scope_violation"
    USER_SCOPE_VIOLATION = "user_scope_violation"
    NO_ELIGIBLE_MODULES = "no_eligible_modules"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _require(value: str, field_name: str) -> None:
    if not str(value or "").strip():
        raise ValueError(f"{field_name} is required")


def _safe(value: Any, *, limit: int = 160) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


@dataclass(frozen=True)
class IntelligenceEvidenceReference:
    evidence_id: str
    source_provider_id: str
    source_mechanism: str
    source_record_ref: str
    observed_at: str
    digest: str | None = None

    @classmethod
    def from_context(
        cls, evidence: ContextEvidenceReference
    ) -> IntelligenceEvidenceReference:
        return cls(
            evidence_id=evidence.evidence_id,
            source_provider_id=evidence.source_provider_id,
            source_mechanism=evidence.source_mechanism,
            source_record_ref=evidence.source_record_ref,
            observed_at=evidence.observed_at,
            digest=evidence.digest,
        )

    def __post_init__(self) -> None:
        _require(self.evidence_id, "evidence_id")
        _require(self.source_provider_id, "source_provider_id")
        _require(self.source_mechanism, "source_mechanism")
        _require(self.source_record_ref, "source_record_ref")
        _require(self.observed_at, "observed_at")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "evidence_id": _safe(self.evidence_id),
            "source_provider_id": _safe(self.source_provider_id),
            "source_mechanism": _safe(self.source_mechanism),
            "source_record_ref": _safe(self.source_record_ref),
            "observed_at": _safe(self.observed_at),
            "digest": _safe(self.digest) if self.digest else None,
        }


@dataclass(frozen=True)
class IntelligenceThreshold:
    threshold_id: str
    operator: str
    value: float
    meaning: str


@dataclass(frozen=True)
class IntelligenceScore:
    score_type: str
    scale: str
    minimum: float
    maximum: float
    value: float
    meaning: str
    calculation_version: str
    inputs: tuple[str, ...]
    thresholds: tuple[IntelligenceThreshold, ...]
    evidence: tuple[IntelligenceEvidenceReference, ...]
    confidence: float
    deterministic: bool

    def __post_init__(self) -> None:
        _require(self.score_type, "score_type")
        _require(self.scale, "scale")
        _require(self.meaning, "meaning")
        _require(self.calculation_version, "calculation_version")
        if self.minimum > self.maximum:
            raise ValueError("score minimum must be <= maximum")
        if not self.minimum <= self.value <= self.maximum:
            raise ValueError("score value out of range")
        if not self.inputs:
            raise ValueError("score inputs are required")
        if not self.evidence:
            raise ValueError("score evidence is required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("score confidence must be between 0.0 and 1.0")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "score_type": self.score_type,
            "scale": self.scale,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "value": self.value,
            "calculation_version": self.calculation_version,
            "input_count": len(self.inputs),
            "evidence_count": len(self.evidence),
            "confidence": self.confidence,
            "deterministic": self.deterministic,
        }


@dataclass(frozen=True)
class ExecutiveIntelligenceSignal:
    signal_id: str
    intelligence_type: str
    title: str
    concise_summary: str
    structured_payload: Mapping[str, Any]
    source_context_ids: tuple[str, ...]
    evidence_references: tuple[IntelligenceEvidenceReference, ...]
    module_id: str
    module_version: str
    generated_at: str
    valid_from: str
    stale_after: str
    freshness_state: str
    tenant_id: str
    user_id: str | None
    scope: str
    severity: str
    priority: str
    confidence: float
    deterministic: bool
    fact_or_inference: str
    sensitivity: str
    tags: tuple[str, ...]
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)
    lifecycle_status: str = "active"
    scores: tuple[IntelligenceScore, ...] = ()

    def __post_init__(self) -> None:
        _require(self.signal_id, "signal_id")
        _require(self.intelligence_type, "intelligence_type")
        _require(self.module_id, "module_id")
        _require(self.module_version, "module_version")
        if self.severity not in SEVERITIES:
            raise ValueError("invalid severity")
        if self.priority not in PRIORITIES:
            raise ValueError("invalid priority")
        if self.freshness_state not in FRESHNESS_STATES:
            raise ValueError("invalid freshness")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.fact_or_inference not in FACT_OR_INFERENCE:
            raise ValueError("invalid fact_or_inference")
        if self.fact_or_inference == "inference" and self.deterministic:
            raise ValueError("inference cannot be labelled deterministic")
        if not self.source_context_ids:
            raise ValueError("source_context_ids are required")
        if not self.evidence_references:
            raise ValueError("evidence is required")
        if not isinstance(self.structured_payload, Mapping):
            raise ValueError("structured_payload must be a mapping")

    def validate_scope(self, *, tenant_id: str, user_id: str | None = None) -> None:
        if self.tenant_id != tenant_id:
            raise ValueError("tenant scope mismatch")
        if user_id and self.user_id is not None and self.user_id != user_id:
            raise ValueError("user scope mismatch")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "intelligence_type": self.intelligence_type,
            "source_context_ids": list(self.source_context_ids),
            "evidence_ids": [item.evidence_id for item in self.evidence_references],
            "module_id": self.module_id,
            "module_version": self.module_version,
            "freshness_state": self.freshness_state,
            "severity": self.severity,
            "priority": self.priority,
            "confidence": round(float(self.confidence), 3),
            "deterministic": self.deterministic,
            "fact_or_inference": self.fact_or_inference,
            "sensitivity": self.sensitivity,
            "tags": list(self.tags),
            "lifecycle_status": self.lifecycle_status,
            "score_count": len(self.scores),
        }


@dataclass(frozen=True)
class IntelligenceError:
    module_id: str
    code: str
    safe_summary: str
    retryable: bool = False

    def safe_trace(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "code": self.code,
            "safe_summary": _safe(self.safe_summary),
            "retryable": self.retryable,
        }


@dataclass(frozen=True)
class IntelligenceModuleDefinition:
    module_id: str
    name: str
    version: str
    owner: str
    description: str
    input_context_types: tuple[str, ...]
    optional_context_types: tuple[str, ...]
    output_intelligence_types: tuple[str, ...]
    deterministic: bool
    required_evidence: bool
    freshness_requirements: tuple[str, ...]
    minimum_context_requirements: tuple[str, ...]
    tenant_scope: str
    user_scope: str
    timeout_ms: int
    execution_priority: int
    risk_level: str
    enabled: bool
    lifecycle_state: str
    calculation_documentation: str
    test_fixture_refs: tuple[str, ...]
    health_state: str = "healthy"

    def __post_init__(self) -> None:
        _require(self.module_id, "module_id")
        _require(self.version, "version")
        if not self.output_intelligence_types:
            raise ValueError("output_intelligence_types must not be empty")


@dataclass(frozen=True)
class IntelligenceSelectionRequest:
    tenant_id: str
    user_id: str | None
    request_classification: str
    ranking_profile: str
    context_snapshot: ExecutiveContextSnapshot
    max_signals: int
    now: str = field(default_factory=_now_iso)


@dataclass(frozen=True)
class IntelligenceExecutionResult:
    module_id: str
    status: str
    signals: tuple[ExecutiveIntelligenceSignal, ...]
    error: IntelligenceError | None = None
    latency_ms: int = 0


@dataclass(frozen=True)
class ExecutiveIntelligenceSnapshot:
    tenant_id: str
    user_id: str | None
    request_classification: str
    ranking_profile: str
    generated_at: str
    signals: tuple[ExecutiveIntelligenceSignal, ...]
    selected_module_ids: tuple[str, ...]
    successful_module_ids: tuple[str, ...]
    failed_module_ids: tuple[str, ...]
    skipped_module_ids: tuple[str, ...]
    errors: tuple[IntelligenceError, ...]
    warnings: tuple[str, ...]
    module_latencies_ms: Mapping[str, int]
    snapshot_digest: str
    output_digest: str
    skipped_signal_count: int = 0

    @property
    def signal_counts_by_type(self) -> Mapping[str, int]:
        return dict(Counter(signal.intelligence_type for signal in self.signals))

    def safe_trace_metadata(self) -> dict[str, Any]:
        severity = Counter(signal.severity for signal in self.signals)
        priority = Counter(signal.priority for signal in self.signals)
        fact_kind = Counter(signal.fact_or_inference for signal in self.signals)
        return {
            "status": "ok",
            "selected_module_ids": list(self.selected_module_ids),
            "successful_module_ids": list(self.successful_module_ids),
            "failed_module_ids": list(self.failed_module_ids),
            "skipped_module_ids": list(self.skipped_module_ids),
            "signal_count": len(self.signals),
            "signal_counts_by_type": dict(self.signal_counts_by_type),
            "severity_summary": dict(severity),
            "priority_summary": dict(priority),
            "deterministic_signal_count": sum(
                1 for signal in self.signals if signal.deterministic
            ),
            "inference_signal_count": fact_kind.get("inference", 0),
            "stale_input_count": sum(
                1 for signal in self.signals if signal.freshness_state == "stale"
            ),
            "evidence_reference_count": sum(
                len(signal.evidence_references) for signal in self.signals
            ),
            "ranking_profile": self.ranking_profile,
            "module_latencies_ms": dict(self.module_latencies_ms),
            "snapshot_digest": self.snapshot_digest,
            "output_digest": self.output_digest,
            "safe_error_codes": [error.code for error in self.errors],
            "skipped_signal_count": self.skipped_signal_count,
        }


class ExecutiveIntelligenceModule(Protocol):
    definition: IntelligenceModuleDefinition

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]: ...


class IntelligenceRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, ExecutiveIntelligenceModule] = {}
        self._enabled_overrides: dict[str, bool] = {}

    def register(self, module: ExecutiveIntelligenceModule) -> None:
        module_id = module.definition.module_id
        if module_id in self._modules:
            raise ValueError(f"duplicate intelligence module: {module_id}")
        self._modules[module_id] = module

    def lookup(self, module_id: str) -> ExecutiveIntelligenceModule | None:
        return self._modules.get(module_id)

    def set_enabled(self, module_id: str, enabled: bool) -> None:
        if module_id not in self._modules:
            raise KeyError(module_id)
        self._enabled_overrides[module_id] = enabled

    def enabled_modules(
        self, *, deterministic_only: bool = False
    ) -> tuple[ExecutiveIntelligenceModule, ...]:
        modules = []
        for module in self._modules.values():
            if not self._module_enabled(module):
                continue
            if module.definition.lifecycle_state != "active":
                continue
            if deterministic_only and not module.definition.deterministic:
                continue
            modules.append(module)
        return tuple(
            sorted(modules, key=lambda item: item.definition.execution_priority)
        )

    def by_input_context_type(
        self, context_type: str
    ) -> tuple[ExecutiveIntelligenceModule, ...]:
        return tuple(
            module
            for module in self.enabled_modules()
            if context_type in module.definition.input_context_types
        )

    def by_output_intelligence_type(
        self, intelligence_type: str
    ) -> tuple[ExecutiveIntelligenceModule, ...]:
        return tuple(
            module
            for module in self.enabled_modules()
            if intelligence_type in module.definition.output_intelligence_types
        )

    def health(self) -> dict[str, dict[str, Any]]:
        return {
            module_id: {
                "enabled": self._module_enabled(module),
                "version": module.definition.version,
                "deterministic": module.definition.deterministic,
                "health_state": module.definition.health_state,
                "lifecycle_state": module.definition.lifecycle_state,
                "input_context_types": list(module.definition.input_context_types),
                "output_intelligence_types": list(
                    module.definition.output_intelligence_types
                ),
            }
            for module_id, module in sorted(self._modules.items())
        }

    def _module_enabled(self, module: ExecutiveIntelligenceModule) -> bool:
        override = self._enabled_overrides.get(module.definition.module_id)
        return module.definition.enabled if override is None else override


class ExecutiveIntelligenceEngine:
    def __init__(self, *, registry: IntelligenceRegistry) -> None:
        self.registry = registry
        self.last_snapshot: ExecutiveIntelligenceSnapshot | None = None

    @classmethod
    def from_modules(
        cls, modules: Iterable[ExecutiveIntelligenceModule]
    ) -> ExecutiveIntelligenceEngine:
        registry = IntelligenceRegistry()
        for module in modules:
            registry.register(module)
        return cls(registry=registry)

    def run(
        self, request: IntelligenceSelectionRequest
    ) -> ExecutiveIntelligenceSnapshot:
        started = time.monotonic()
        available_types = {
            item.context_type for item in request.context_snapshot.contributions
        }
        selected: list[ExecutiveIntelligenceModule] = []
        skipped: list[str] = []
        for module in self.registry.enabled_modules(deterministic_only=True):
            required = set(module.definition.minimum_context_requirements)
            if required and not required.intersection(available_types):
                if module.definition.module_id != "context_availability":
                    skipped.append(module.definition.module_id)
                    continue
            selected.append(module)

        signals: list[ExecutiveIntelligenceSignal] = []
        errors: list[IntelligenceError] = []
        successful: list[str] = []
        failed: list[str] = []
        warnings: list[str] = []
        latencies: dict[str, int] = {}
        skipped_signal_count = 0
        seen: set[tuple[str, tuple[str, ...], str]] = set()

        for module in selected:
            module_id = module.definition.module_id
            module_started = time.monotonic()
            try:
                produced = tuple(module.execute(request))
                latency_ms = int((time.monotonic() - module_started) * 1000)
                latencies[module_id] = latency_ms
                if latency_ms > module.definition.timeout_ms:
                    raise TimeoutError("intelligence module timeout")
                accepted = 0
                for signal in produced:
                    try:
                        signal.validate_scope(
                            tenant_id=request.tenant_id,
                            user_id=request.user_id,
                        )
                        _validate_signal_output(signal, module)
                    except ValueError as exc:
                        skipped_signal_count += 1
                        warnings.append(f"signal_rejected:{module_id}:{_safe(exc)}")
                        continue
                    key = (
                        signal.intelligence_type,
                        tuple(sorted(signal.source_context_ids)),
                        signal.module_id,
                    )
                    if key in seen:
                        skipped_signal_count += 1
                        warnings.append(f"duplicate_signal:{signal.signal_id}")
                        continue
                    seen.add(key)
                    signals.append(signal)
                    accepted += 1
                successful.append(module_id)
                if accepted < len(produced):
                    warnings.append(f"module_partial_accept:{module_id}")
            except TimeoutError:
                failed.append(module_id)
                errors.append(
                    IntelligenceError(
                        module_id=module_id,
                        code=IntelligenceErrorCode.MODULE_TIMEOUT,
                        safe_summary="Intelligence module timed out.",
                        retryable=True,
                    )
                )
            except Exception:
                failed.append(module_id)
                errors.append(
                    IntelligenceError(
                        module_id=module_id,
                        code=IntelligenceErrorCode.MODULE_EXCEPTION,
                        safe_summary="Intelligence module failed.",
                        retryable=False,
                    )
                )

        ranked = _rank_signals(signals, profile=request.ranking_profile)
        if len(ranked) > max(0, request.max_signals):
            skipped_signal_count += len(ranked) - max(0, request.max_signals)
            ranked = ranked[: max(0, request.max_signals)]
            warnings.append("signal_budget_applied")
        if not selected:
            errors.append(
                IntelligenceError(
                    module_id="engine",
                    code=IntelligenceErrorCode.NO_ELIGIBLE_MODULES,
                    safe_summary="No intelligence modules were eligible.",
                )
            )
        digest_seed = [signal.safe_trace() for signal in ranked]
        output = render_intelligence_snapshot_for_reasoning_items(ranked)
        snapshot = ExecutiveIntelligenceSnapshot(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            request_classification=request.request_classification,
            ranking_profile=request.ranking_profile,
            generated_at=request.now,
            signals=tuple(ranked),
            selected_module_ids=tuple(
                module.definition.module_id for module in selected
            ),
            successful_module_ids=tuple(successful),
            failed_module_ids=tuple(failed),
            skipped_module_ids=tuple(skipped),
            errors=tuple(errors),
            warnings=tuple(warnings),
            module_latencies_ms=latencies,
            snapshot_digest=f"intel_{_digest(json.dumps(digest_seed, sort_keys=True))[:16]}",
            output_digest=f"intel_out_{_digest(output)[:16]}",
            skipped_signal_count=skipped_signal_count,
        )
        self.last_snapshot = snapshot
        del started
        return snapshot


def _validate_signal_output(
    signal: ExecutiveIntelligenceSignal,
    module: ExecutiveIntelligenceModule,
) -> None:
    if signal.module_id != module.definition.module_id:
        raise ValueError("module mismatch")
    if signal.intelligence_type not in module.definition.output_intelligence_types:
        raise ValueError("unsupported intelligence type")
    if module.definition.required_evidence and not signal.evidence_references:
        raise ValueError("missing evidence")


def _rank_signals(
    signals: list[ExecutiveIntelligenceSignal],
    *,
    profile: str,
) -> list[ExecutiveIntelligenceSignal]:
    priority_weight = {
        "urgent": 0,
        "attention": 1,
        "normal": 2,
        "background": 3,
    }
    severity_weight = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "informational": 4,
    }
    profile_weight = {
        "direct_request": {
            "meeting_conflict": -3,
            "commitment_overdue": -3,
            "required_context_unavailable": -2,
        },
        "morning_brief": {
            "commitment_overdue": -4,
            "meeting_conflict": -3,
            "preparation_gap": -2,
        },
        "schedule_review": {
            "meeting_conflict": -4,
            "longest_focus_block": -3,
            "back_to_back_meeting_count": -2,
        },
    }.get(profile, {})
    return sorted(
        signals,
        key=lambda signal: (
            profile_weight.get(signal.intelligence_type, 0),
            priority_weight[signal.priority],
            severity_weight[signal.severity],
            -float(signal.confidence),
            signal.generated_at,
            signal.module_id,
            signal.signal_id,
        ),
    )


def _definition(
    *,
    module_id: str,
    name: str,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
    priority: int,
    docs: str,
) -> IntelligenceModuleDefinition:
    return IntelligenceModuleDefinition(
        module_id=module_id,
        name=name,
        version="1.0.0",
        owner="Hermes",
        description=docs,
        input_context_types=inputs,
        optional_context_types=(),
        output_intelligence_types=outputs,
        deterministic=True,
        required_evidence=True,
        freshness_requirements=("current", "stale"),
        minimum_context_requirements=inputs,
        tenant_scope="tenant",
        user_scope="user",
        timeout_ms=100,
        execution_priority=priority,
        risk_level="low",
        enabled=True,
        lifecycle_state="active",
        calculation_documentation=docs,
        test_fixture_refs=("synthetic_acceptance_v1",),
    )


@dataclass(frozen=True)
class _Meeting:
    contribution: ExecutiveContextContribution
    start: datetime
    end: datetime
    all_day: bool
    external_attendee_count: int
    strategic: bool
    preparation_refs: tuple[str, ...]

    @property
    def minutes(self) -> int:
        return max(0, int((self.end - self.start).total_seconds() // 60))


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _meetings(snapshot: ExecutiveContextSnapshot) -> list[_Meeting]:
    meetings: list[_Meeting] = []
    for item in snapshot.contributions:
        if item.context_type != "meeting":
            continue
        payload = item.payload
        if str(payload.get("status") or "").casefold() == "cancelled":
            continue
        if str(payload.get("response_status") or "").casefold() == "declined":
            continue
        start = _parse_dt(payload.get("start"))
        end = _parse_dt(payload.get("end"))
        if start is None or end is None or end <= start:
            continue
        meetings.append(
            _Meeting(
                contribution=item,
                start=start,
                end=end,
                all_day=bool(payload.get("all_day")),
                external_attendee_count=int(
                    payload.get("external_attendee_count") or 0
                ),
                strategic=bool(payload.get("strategic")),
                preparation_refs=tuple(
                    str(ref) for ref in payload.get("preparation_refs") or ()
                ),
            )
        )
    return sorted(
        meetings,
        key=lambda item: (item.start, item.end, item.contribution.contribution_id),
    )


def _context_evidence(
    item: ExecutiveContextContribution,
) -> tuple[IntelligenceEvidenceReference, ...]:
    return tuple(
        IntelligenceEvidenceReference.from_context(ref) for ref in item.evidence_refs
    )


def _signal(
    *,
    request: IntelligenceSelectionRequest,
    module: IntelligenceModuleDefinition,
    intelligence_type: str,
    title: str,
    summary: str,
    payload: Mapping[str, Any],
    sources: tuple[ExecutiveContextContribution, ...],
    severity: str = "low",
    priority: str = "normal",
    fact_or_inference: str = "deterministic_signal",
    confidence: float = 1.0,
    stale_after: str | None = None,
    tags: tuple[str, ...] = (),
    scores: tuple[IntelligenceScore, ...] = (),
) -> ExecutiveIntelligenceSignal:
    evidence = tuple(
        evidence for source in sources for evidence in _context_evidence(source)
    )
    source_ids = tuple(source.contribution_id for source in sources)
    seed = json.dumps(
        {
            "module": module.module_id,
            "type": intelligence_type,
            "sources": source_ids,
            "payload": dict(payload),
        },
        sort_keys=True,
        default=str,
    )
    return ExecutiveIntelligenceSignal(
        signal_id=f"intel:{module.module_id}:{_digest(seed)[:16]}",
        intelligence_type=intelligence_type,
        title=title,
        concise_summary=summary,
        structured_payload=dict(payload),
        source_context_ids=source_ids,
        evidence_references=evidence,
        module_id=module.module_id,
        module_version=module.version,
        generated_at=request.now,
        valid_from=request.now,
        stale_after=stale_after or request.now,
        freshness_state="stale"
        if any(source.freshness_state == "stale" for source in sources)
        else "current",
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        scope="user" if request.user_id else "tenant",
        severity=severity,
        priority=priority,
        confidence=confidence,
        deterministic=True,
        fact_or_inference=fact_or_inference,
        sensitivity="private",
        tags=tags,
        scores=scores,
    )


class ScheduleSummaryModule:
    definition = _definition(
        module_id="schedule_summary",
        name="Schedule Summary",
        inputs=("meeting",),
        outputs=(
            "meeting_count",
            "scheduled_duration",
            "next_meeting",
            "first_meeting",
            "final_meeting",
        ),
        priority=10,
        docs="Counts timed meetings and derives first/next/final meeting from supplied meeting context.",
    )

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        meetings = _meetings(request.context_snapshot)
        if not meetings:
            return ()
        timed = [meeting for meeting in meetings if not meeting.all_day]
        source_tuple = tuple(meeting.contribution for meeting in meetings)
        total_minutes = sum(meeting.minutes for meeting in timed)
        signals = [
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="meeting_count",
                title="Meeting count",
                summary=f"{len(meetings)} meeting(s) are represented in supplied context.",
                payload={
                    "meeting_count": len(meetings),
                    "timed_meeting_count": len(timed),
                },
                sources=source_tuple,
                fact_or_inference="derived_fact",
                tags=("schedule", "derived_fact"),
            ),
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="scheduled_duration",
                title="Scheduled duration",
                summary=f"{total_minutes} scheduled meeting minutes are represented in supplied context.",
                payload={"scheduled_minutes": total_minutes},
                sources=source_tuple,
                fact_or_inference="derived_fact",
                tags=("schedule", "duration"),
            ),
        ]
        now = _parse_dt(request.now) or datetime.now().astimezone()
        upcoming = next(
            (meeting for meeting in timed if meeting.end >= now),
            timed[0] if timed else None,
        )
        first = timed[0] if timed else meetings[0]
        final = timed[-1] if timed else meetings[-1]
        for kind, meeting in (
            ("next_meeting", upcoming),
            ("first_meeting", first),
            ("final_meeting", final),
        ):
            if meeting is None:
                continue
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type=kind,
                    title=kind.replace("_", " ").title(),
                    summary=f"{kind} is identified from supplied meeting start/end fields.",
                    payload={
                        "meeting_ref": meeting.contribution.contribution_id,
                        "start": meeting.start.isoformat(),
                        "end": meeting.end.isoformat(),
                    },
                    sources=(meeting.contribution,),
                    fact_or_inference="derived_fact",
                    tags=("schedule", kind),
                )
            )
        return tuple(signals)


class ScheduleConflictModule:
    definition = _definition(
        module_id="calendar_conflict",
        name="Calendar Conflict",
        inputs=("meeting",),
        outputs=("meeting_conflict", "overlapping_minutes"),
        priority=20,
        docs="Detects overlap between timed meeting intervals; back-to-back meetings are not conflicts.",
    )

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        meetings = [
            meeting
            for meeting in _meetings(request.context_snapshot)
            if not meeting.all_day
        ]
        signals: list[ExecutiveIntelligenceSignal] = []
        for previous, current in zip(meetings, meetings[1:], strict=False):
            if current.start >= previous.end:
                continue
            minutes = max(
                0,
                int(
                    (min(previous.end, current.end) - current.start).total_seconds()
                    // 60
                ),
            )
            sources = (previous.contribution, current.contribution)
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type="meeting_conflict",
                    title="Meeting conflict",
                    summary=f"{minutes} overlapping minute(s) detected between supplied meetings.",
                    payload={
                        "overlapping_minutes": minutes,
                        "meeting_refs": [source.contribution_id for source in sources],
                    },
                    sources=sources,
                    severity="medium",
                    priority="attention",
                    tags=("schedule", "conflict"),
                )
            )
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type="overlapping_minutes",
                    title="Overlapping minutes",
                    summary=f"{minutes} overlapping minute(s) were calculated deterministically.",
                    payload={"minutes": minutes},
                    sources=sources,
                    fact_or_inference="derived_fact",
                    tags=("schedule", "conflict", "duration"),
                )
            )
        return tuple(signals)


class FocusTimeModule:
    definition = _definition(
        module_id="focus_time",
        name="Focus Time",
        inputs=("meeting",),
        outputs=(
            "free_time",
            "longest_focus_block",
            "focus_block_count",
            "fragmented_day",
        ),
        priority=30,
        docs="Calculates free blocks inside configured working hours using supplied timed meetings.",
    )

    def __init__(
        self, *, workday_start: str = "09:00", workday_end: str = "17:30"
    ) -> None:
        self.workday_start = _clock(workday_start)
        self.workday_end = _clock(workday_end)

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        meetings = [
            meeting
            for meeting in _meetings(request.context_snapshot)
            if not meeting.all_day
        ]
        if not meetings:
            return ()
        day = meetings[0].start.date()
        tz = meetings[0].start.tzinfo
        start = datetime.combine(day, self.workday_start, tzinfo=tz)
        end = datetime.combine(day, self.workday_end, tzinfo=tz)
        blocks = _free_blocks(meetings, start=start, end=end)
        longest = max(
            (
                int((block_end - block_start).total_seconds() // 60)
                for block_start, block_end in blocks
            ),
            default=0,
        )
        total = sum(
            int((block_end - block_start).total_seconds() // 60)
            for block_start, block_end in blocks
        )
        sources = tuple(meeting.contribution for meeting in meetings)
        signals = [
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="free_time",
                title="Free time",
                summary=f"{total} free working minutes are represented between meetings.",
                payload={
                    "minutes": total,
                    "assumption": "working_hours_default_09_00_17_30",
                },
                sources=sources,
                fact_or_inference="derived_fact",
                tags=("schedule", "focus"),
            ),
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="longest_focus_block",
                title="Longest focus block",
                summary=f"Longest focus block is {longest} minutes.",
                payload={"minutes": longest, "block_count": len(blocks)},
                sources=sources,
                fact_or_inference="derived_fact",
                tags=("schedule", "focus"),
            ),
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="focus_block_count",
                title="Focus block count",
                summary=f"{len(blocks)} focus block(s) were calculated.",
                payload={"count": len(blocks)},
                sources=sources,
                fact_or_inference="derived_fact",
                tags=("schedule", "focus"),
            ),
        ]
        if len(blocks) >= 4 or longest < 90:
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type="fragmented_day",
                    title="Fragmented day",
                    summary="The day appears fragmented by deterministic focus-time thresholds.",
                    payload={
                        "longest_focus_block_minutes": longest,
                        "focus_block_count": len(blocks),
                    },
                    sources=sources,
                    severity="medium",
                    priority="attention",
                    tags=("schedule", "focus", "fragmentation"),
                )
            )
        return tuple(signals)


def _clock(value: str) -> dt_time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return dt_time(hour=hour, minute=minute)


def _free_blocks(
    meetings: list[_Meeting],
    *,
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, datetime]]:
    cursor = start
    blocks: list[tuple[datetime, datetime]] = []
    for meeting in meetings:
        meeting_start = max(meeting.start, start)
        meeting_end = min(meeting.end, end)
        if meeting_end <= start or meeting_start >= end:
            continue
        if meeting_start > cursor:
            blocks.append((cursor, meeting_start))
        if meeting_end > cursor:
            cursor = meeting_end
    if cursor < end:
        blocks.append((cursor, end))
    return [
        (block_start, block_end)
        for block_start, block_end in blocks
        if block_end > block_start
    ]


class BackToBackLoadModule:
    definition = _definition(
        module_id="back_to_back_load",
        name="Back-to-Back Load",
        inputs=("meeting",),
        outputs=(
            "back_to_back_meeting_count",
            "longest_back_to_back_sequence",
            "meeting_load",
        ),
        priority=40,
        docs="Counts adjacent meetings separated by a small gap threshold; overlaps are handled by conflict module.",
    )

    def __init__(self, *, gap_threshold_minutes: int = 10) -> None:
        self.gap_threshold_minutes = gap_threshold_minutes

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        meetings = [
            meeting
            for meeting in _meetings(request.context_snapshot)
            if not meeting.all_day
        ]
        pairs = []
        longest = 1 if meetings else 0
        current_sequence = 1
        for previous, current in zip(meetings, meetings[1:], strict=False):
            gap = int((current.start - previous.end).total_seconds() // 60)
            if 0 <= gap <= self.gap_threshold_minutes:
                pairs.append((previous, current))
                current_sequence += 1
                longest = max(longest, current_sequence)
            elif gap >= 0:
                current_sequence = 1
        if not meetings:
            return ()
        sources = tuple(meeting.contribution for meeting in meetings)
        return (
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="back_to_back_meeting_count",
                title="Back-to-back meeting count",
                summary=f"{len(pairs)} back-to-back meeting pair(s) found.",
                payload={
                    "count": len(pairs),
                    "gap_threshold_minutes": self.gap_threshold_minutes,
                },
                sources=sources,
                fact_or_inference="derived_fact",
                tags=("schedule", "load"),
            ),
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="longest_back_to_back_sequence",
                title="Longest back-to-back sequence",
                summary=f"Longest back-to-back sequence contains {longest} meeting(s).",
                payload={"count": longest},
                sources=sources,
                fact_or_inference="derived_fact",
                tags=("schedule", "load"),
            ),
            _signal(
                request=request,
                module=self.definition,
                intelligence_type="meeting_load",
                title="Meeting load",
                summary="Meeting load was calculated from supplied meeting count and adjacency.",
                payload={
                    "meeting_count": len(meetings),
                    "back_to_back_pairs": len(pairs),
                },
                sources=sources,
                severity="medium" if len(pairs) else "low",
                priority="attention" if len(pairs) else "normal",
                tags=("schedule", "load"),
            ),
        )


class PreparationGapModule:
    definition = _definition(
        module_id="preparation_gap",
        name="Preparation Gap",
        inputs=("meeting",),
        outputs=("preparation_gap",),
        priority=50,
        docs="Flags external or explicitly strategic meetings within 48 hours when no preparation reference is linked.",
    )

    def __init__(self, *, horizon_hours: int = 48) -> None:
        self.horizon_hours = horizon_hours

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        now = _parse_dt(request.now) or datetime.now().astimezone()
        horizon = now + timedelta(hours=self.horizon_hours)
        signals = []
        for meeting in _meetings(request.context_snapshot):
            if meeting.start > horizon:
                continue
            if meeting.preparation_refs:
                continue
            if not (meeting.external_attendee_count > 0 or meeting.strategic):
                continue
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type="preparation_gap",
                    title="Preparation gap",
                    summary="A strategic or external meeting lacks a linked preparation record.",
                    payload={
                        "meeting_ref": meeting.contribution.contribution_id,
                        "horizon_hours": self.horizon_hours,
                    },
                    sources=(meeting.contribution,),
                    severity="medium",
                    priority="attention",
                    tags=("schedule", "preparation"),
                )
            )
        return tuple(signals)


class CommitmentDueModule:
    definition = _definition(
        module_id="commitment_due",
        name="Commitment Due",
        inputs=("commitment",),
        outputs=("commitment_due", "commitment_overdue"),
        priority=60,
        docs="Detects due and overdue commitments from supplied due_at/due_date fields.",
    )

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        now = _parse_dt(request.now) or datetime.now().astimezone()
        signals = []
        for item in request.context_snapshot.contributions:
            if item.context_type != "commitment":
                continue
            status = str(item.payload.get("status") or "open").casefold()
            if status in {"complete", "completed", "done", "closed"}:
                continue
            due = _parse_dt(item.payload.get("due_at") or item.payload.get("due_date"))
            if due is None:
                continue
            if due.date() < now.date():
                kind = "commitment_overdue"
                severity = "high"
                priority = "urgent"
            elif due.date() == now.date():
                kind = "commitment_due"
                severity = "medium"
                priority = "attention"
            else:
                continue
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type=kind,
                    title=kind.replace("_", " ").title(),
                    summary=f"{kind} detected from supplied commitment deadline.",
                    payload={
                        "commitment_ref": item.contribution_id,
                        "due_at": due.isoformat(),
                    },
                    sources=(item,),
                    severity=severity,
                    priority=priority,
                    fact_or_inference="derived_fact",
                    tags=("commitment", kind),
                )
            )
        return tuple(signals)


class ContextAvailabilityModule:
    definition = _definition(
        module_id="context_availability",
        name="Context Availability",
        inputs=("capability_status",),
        outputs=(
            "required_context_unavailable",
            "stale_data_warning",
            "provider_degraded",
        ),
        priority=5,
        docs="Turns provider status and snapshot warnings into capability-honest limitation signals.",
    )

    def execute(
        self, request: IntelligenceSelectionRequest
    ) -> tuple[ExecutiveIntelligenceSignal, ...]:
        signals = []
        for item in request.context_snapshot.contributions:
            if item.context_type != "capability_status":
                continue
            status = str(
                item.payload.get("status") or item.payload.get("health_state") or ""
            ).casefold()
            provider_id = str(
                item.payload.get("provider_id") or item.source_provider_id
            )
            if status in {"connected", "healthy", "ok", "available", ""}:
                continue
            kind = (
                "provider_degraded"
                if "degraded" in status
                else "required_context_unavailable"
            )
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type=kind,
                    title="Context availability limitation",
                    summary="A required context source is unavailable or degraded.",
                    payload={"provider_id": provider_id, "status": status or "unknown"},
                    sources=(item,),
                    severity="medium",
                    priority="attention",
                    tags=("capability", "limitation"),
                )
            )
        for warning in request.context_snapshot.warnings:
            if "stale" not in warning.casefold():
                continue
            source = (
                request.context_snapshot.contributions[0]
                if request.context_snapshot.contributions
                else None
            )
            if source is None:
                continue
            signals.append(
                _signal(
                    request=request,
                    module=self.definition,
                    intelligence_type="stale_data_warning",
                    title="Stale data warning",
                    summary="Context snapshot reported stale data.",
                    payload={"warning_digest": _digest(warning)[:12]},
                    sources=(source,),
                    severity="low",
                    priority="normal",
                    tags=("capability", "stale"),
                )
            )
        return tuple(signals)


def build_default_intelligence_registry() -> IntelligenceRegistry:
    registry = IntelligenceRegistry()
    for module in (
        ContextAvailabilityModule(),
        ScheduleSummaryModule(),
        ScheduleConflictModule(),
        FocusTimeModule(),
        BackToBackLoadModule(),
        PreparationGapModule(),
        CommitmentDueModule(),
    ):
        registry.register(module)
    return registry


def build_default_intelligence_engine() -> ExecutiveIntelligenceEngine:
    return ExecutiveIntelligenceEngine(registry=build_default_intelligence_registry())


def is_executive_intelligence_enabled() -> bool:
    value = os.getenv("HERMES_EXECUTIVE_INTELLIGENCE_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_intelligence_registry_enabled() -> bool:
    value = os.getenv("HERMES_INTELLIGENCE_REGISTRY_ENABLED")
    return True if value is None else is_truthy_value(value)


def are_deterministic_intelligence_modules_enabled() -> bool:
    value = os.getenv("HERMES_DETERMINISTIC_INTELLIGENCE_MODULES_ENABLED")
    return True if value is None else is_truthy_value(value)


def are_inference_intelligence_modules_enabled() -> bool:
    return is_truthy_value(os.getenv("HERMES_INFERENCE_INTELLIGENCE_MODULES_ENABLED"))


def render_intelligence_snapshot_for_reasoning(
    snapshot: ExecutiveIntelligenceSnapshot,
    *,
    max_chars: int,
) -> str:
    rendered = render_intelligence_snapshot_for_reasoning_items(snapshot.signals)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max(0, max_chars - 30)].rstrip() + "\n[intelligence truncated]"


def render_intelligence_snapshot_for_reasoning_items(
    signals: tuple[ExecutiveIntelligenceSignal, ...]
    | list[ExecutiveIntelligenceSignal],
) -> str:
    if not signals:
        return (
            "Executive Intelligence:\n"
            "- Derived executive facts: none\n"
            "- Attention signals: none\n"
            "- Data limitations: none\n"
            "- Execution boundary: not_executed"
        )
    facts = [
        signal
        for signal in signals
        if signal.fact_or_inference in {"source_fact", "derived_fact"}
    ]
    attention = [
        signal
        for signal in signals
        if signal.fact_or_inference == "deterministic_signal"
        and signal.intelligence_type
        not in {
            "required_context_unavailable",
            "stale_data_warning",
            "provider_degraded",
        }
    ]
    limitations = [
        signal
        for signal in signals
        if signal.intelligence_type
        in {"required_context_unavailable", "stale_data_warning", "provider_degraded"}
    ]
    sections = ["Executive Intelligence:"]
    sections.append("- Derived executive facts:")
    sections.extend(_render_signal_lines(facts))
    sections.append("- Attention signals:")
    sections.extend(_render_signal_lines(attention))
    sections.append("- Data limitations:")
    sections.extend(_render_signal_lines(limitations))
    sections.append("- Execution boundary: not_executed")
    return "\n".join(sections)


def _render_signal_lines(signals: list[ExecutiveIntelligenceSignal]) -> list[str]:
    if not signals:
        return ["  - none"]
    selected = signals[:5]
    lines = [
        (
            f"  - [{signal.signal_id}] {signal.intelligence_type}: "
            f"{_safe(signal.concise_summary, limit=160)} "
            f"evidence={','.join(signal.source_context_ids[:3])} "
            f"priority={signal.priority} severity={signal.severity}"
        )
        for signal in selected
    ]
    if len(signals) > len(selected):
        lines.append(
            f"  - {len(signals) - len(selected)} more signal(s) omitted by composer budget"
        )
    return lines
