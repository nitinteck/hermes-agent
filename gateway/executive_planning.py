"""Deterministic Executive Planning Engine for Hermes.

The v1 Planning Engine converts a safe ReasoningPlan into bounded candidate
plans. It produces proposals only: no approvals, executions, integrations,
subprocesses, shell commands, or external mutations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
import re
import time
from typing import Any, cast

PROPOSED = "proposed"
NOT_REQUESTED = "not_requested"
NOT_EXECUTED = "not_executed"
PLANNING_LIMITATION = (
    "This is a proposed plan only. It has not been approved or executed; "
    "external execution remains unavailable until a controlled approval and "
    "execution boundary is implemented and explicitly authorised."
)


@dataclass(frozen=True)
class PlanObjective:
    objective_id: str
    summary: str
    desired_outcome: str = ""
    completion_definition: str = ""
    time_horizon: str | None = None
    scope: str = "request_scoped"
    excluded_scope: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def safe_trace(self) -> dict[str, Any]:
        return {
            "objective_id": _safe_label(self.objective_id),
            "summary_digest": _digest(self.summary)[:16],
            "evidence_refs": [_safe_label(ref) for ref in self.evidence_refs],
        }


@dataclass(frozen=True)
class PlanConstraint:
    constraint_id: str
    summary: str
    mandatory: bool = True
    constraint_type: str = "safety"
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanAssumption:
    assumption_id: str
    summary: str
    confidence: str = "assumed"
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanWorkstream:
    workstream_id: str
    title: str
    objective: str
    sequence: int
    owner_requirement_ids: tuple[str, ...] = ()
    success_measure_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanMilestone:
    milestone_id: str
    title: str
    success_measure_ids: tuple[str, ...] = ()
    sequence: int = 1
    completion_condition: str = "Observable completion evidence is available."
    target_date: str | None = None
    evidence_refs: tuple[str, ...] = ()
    status: str = PROPOSED
    execution_status: str = NOT_EXECUTED

    def __post_init__(self) -> None:
        _require_value("status", self.status, {PROPOSED})
        _require_value("execution_status", self.execution_status, {NOT_EXECUTED})
        if not self.completion_condition.strip():
            raise ValueError("milestone completion_condition is required")


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    title: str
    sequence: int
    workstream_id: str | None = None
    milestone_id: str | None = None
    description: str = ""
    step_type: str = "planning"
    prerequisites: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    expected_output: str = "Proposal artefact or decision-ready evidence."
    success_condition: str = "The proposed step output is ready for human review."
    owner_requirement: str | None = None
    owner_requirement_ids: tuple[str, ...] = ()
    resource_requirement_ids: tuple[str, ...] = ()
    dependency_ids: tuple[str, ...] = ()
    estimated_effort: str | None = None
    estimated_duration: str | None = None
    earliest_start: str | None = None
    target_date: str | None = None
    criticality: str = "medium"
    reversibility: str = "reversible"
    approval_requirement: str | None = None
    approval_requirement_ids: tuple[str, ...] = ()
    proposed_action_reference_ids: tuple[str, ...] = ()
    capability_requirements: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    status: str = PROPOSED
    execution_status: str = NOT_EXECUTED

    def __post_init__(self) -> None:
        _require_value("status", self.status, {PROPOSED})
        _require_value("execution_status", self.execution_status, {NOT_EXECUTED})
        if _contains_command_like_payload(self.title) or _contains_command_like_payload(
            self.description
        ):
            raise ValueError("plan step cannot contain shell-like execution payloads")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "step_id": _safe_label(self.step_id),
            "title_digest": _digest(self.title)[:16],
            "sequence": self.sequence,
            "dependency_count": len(self.dependency_ids),
            "approval_requirement_count": len(self.approval_requirement_ids),
            "proposed_action_reference_count": len(self.proposed_action_reference_ids),
            "status": self.status,
            "execution_status": self.execution_status,
        }


@dataclass(frozen=True)
class PlanDependency:
    dependency_id: str
    predecessor_id: str
    successor_id: str
    dependency_type: str = "finish_before_start"
    description: str = ""
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanDecisionPoint:
    decision_point_id: str
    title: str
    required_before_step_id: str | None = None
    evidence_required: tuple[str, ...] = ()
    approval_requirement_id: str | None = None
    risk_class: str = "medium"
    status: str = "open"


@dataclass(frozen=True)
class PlanRisk:
    risk_id: str
    summary: str
    severity: str = "medium"
    likelihood: str = "unknown"
    impact: str = "unknown"
    mitigation_ids: tuple[str, ...] = ()
    status: str = "open"
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanMitigation:
    mitigation_id: str
    risk_id: str
    summary: str
    owner_requirement_id: str | None = None
    expected_effect: str = "reduce_likelihood_or_impact"


@dataclass(frozen=True)
class PlanSuccessMeasure:
    measure_id: str
    summary: str
    target_state: str
    measurement_method: str = "human_review"
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanResourceRequirement:
    requirement_id: str
    summary: str
    resource_type: str = "unknown"
    availability: str = "unconfirmed"
    confidence: str = "unknown"


@dataclass(frozen=True)
class PlanOwnerRequirement:
    requirement_id: str
    summary: str
    required_role: str = "owner"
    required_user_id: str | None = None
    confidence: str = "unknown"


@dataclass(frozen=True)
class PlanEvaluationCriterion:
    criterion_id: str
    title: str
    weight: int
    rationale: str
    description: str = ""
    scale: str = "1-5"
    calculation_method: str = "bounded_deterministic_rating"
    evidence: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    confidence: str = "derived"


@dataclass(frozen=True)
class PlanEvaluation:
    evaluation_id: str
    candidate_plan_id: str
    criterion_ratings: Mapping[str, int]
    criterion_rationales: Mapping[str, str]
    total_score: int
    summary: str
    criteria: tuple[PlanEvaluationCriterion, ...] = ()
    formula: str = "sum(rating * weight)"

    def safe_trace(self) -> dict[str, Any]:
        return {
            "evaluation_id": _safe_label(self.evaluation_id),
            "candidate_plan_id": _safe_label(self.candidate_plan_id),
            "criterion_count": len(self.criterion_ratings),
            "total_score": self.total_score,
            "summary_digest": _digest(self.summary)[:16],
        }


@dataclass(frozen=True)
class ApprovalRequirement:
    approval_requirement_id: str
    summary: str
    approval_class: str = "human_authorisation"
    reason: str = "Future external or high-impact action requires approval."
    required_before_step_ids: tuple[str, ...] = ()
    required_before_capability_ids: tuple[str, ...] = ()
    required_approver_role: str = "authorised_human_actor"
    required_approver_user_id: str | None = None
    evidence_summary: str = ""
    risk_class: str = "medium"
    status: str = NOT_REQUESTED
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    required_role: str = "authorised_human_actor"
    approval_status: str = NOT_REQUESTED

    def __post_init__(self) -> None:
        _require_value("approval_status", self.approval_status, {NOT_REQUESTED})
        _require_value("status", self.status, {NOT_REQUESTED})


@dataclass(frozen=True)
class ProposedActionReference:
    proposed_action_reference_id: str
    action_type: str
    summary: str
    related_step_id: str | None = None
    capability_id: str | None = None
    external_system: str | None = None
    risk_class: str = "medium"
    reversibility: str = "unknown"
    approval_required: bool = True
    approval_requirement_id: str | None = None
    payload_schema_reference: str | None = None
    payload_preview_safe: Mapping[str, Any] | None = None
    evidence_references: tuple[str, ...] = ()
    adapter_id: str | None = None
    external_payload: Mapping[str, Any] | None = None
    approval_status: str = NOT_REQUESTED
    execution_status: str = NOT_EXECUTED

    def __post_init__(self) -> None:
        _require_value("approval_status", self.approval_status, {NOT_REQUESTED})
        _require_value("execution_status", self.execution_status, {NOT_EXECUTED})
        if self.adapter_id is not None:
            raise ValueError("proposed actions cannot bind external adapters in v1")
        if self.external_payload is not None:
            raise ValueError("proposed actions cannot contain external payloads in v1")
        if _contains_command_like_payload(self.summary):
            raise ValueError("proposed actions cannot contain shell-like payloads")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "proposed_action_reference_id": _safe_label(
                self.proposed_action_reference_id
            ),
            "action_type": _safe_label(self.action_type),
            "summary_digest": _digest(self.summary)[:16],
            "approval_status": self.approval_status,
            "execution_status": self.execution_status,
            "adapter_bound": False,
            "external_payload_present": False,
        }


@dataclass(frozen=True)
class PlanRecommendation:
    recommended_plan_id: str
    rationale: str
    tradeoffs: tuple[str, ...] = ()
    alternate_conditions: tuple[str, ...] = ()
    unresolved_assumptions: tuple[str, ...] = ()
    approval_status: str = NOT_REQUESTED
    execution_status: str = NOT_EXECUTED

    def __post_init__(self) -> None:
        _require_value("approval_status", self.approval_status, {NOT_REQUESTED})
        _require_value("execution_status", self.execution_status, {NOT_EXECUTED})


@dataclass(frozen=True)
class PlanningEvidenceReference:
    evidence_id: str
    source_category: str
    confidence: str = "derived"


@dataclass(frozen=True)
class PlanningError:
    code: str
    safe_message: str
    severity: str = "error"


@dataclass(frozen=True)
class ExecutivePlan:
    plan_id: str
    planning_request_id: str
    strategy_id: str
    objective: PlanObjective
    version: int = 1
    tenant_id: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    reasoning_plan_id: str | None = None
    concise_summary: str = ""
    scope: str = "request_scoped"
    constraints: tuple[PlanConstraint, ...] = ()
    assumptions: tuple[PlanAssumption, ...] = ()
    workstreams: tuple[PlanWorkstream, ...] = ()
    milestones: tuple[PlanMilestone, ...] = ()
    steps: tuple[PlanStep, ...] = ()
    dependencies: tuple[PlanDependency, ...] = ()
    decision_points: tuple[PlanDecisionPoint, ...] = ()
    risks: tuple[PlanRisk, ...] = ()
    mitigations: tuple[PlanMitigation, ...] = ()
    success_measures: tuple[PlanSuccessMeasure, ...] = ()
    resource_requirements: tuple[PlanResourceRequirement, ...] = ()
    owner_requirements: tuple[PlanOwnerRequirement, ...] = ()
    candidate_plans: tuple[str, ...] = ()
    recommended_candidate_id: str | None = None
    evaluation: PlanEvaluation | None = None
    recommendation: PlanRecommendation | None = None
    evidence_refs: tuple[PlanningEvidenceReference, ...] = ()
    approval_requirements: tuple[ApprovalRequirement, ...] = ()
    proposed_actions: tuple[ProposedActionReference, ...] = ()
    limitations: tuple[str, ...] = (PLANNING_LIMITATION,)
    confidence: str = "unknown"
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    valid_from: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    stale_after: str = field(
        default_factory=lambda: (datetime.now(UTC) + timedelta(days=7)).isoformat()
    )
    sensitivity: str = "internal"
    lifecycle_state: str = PROPOSED
    plan_status: str = PROPOSED
    approval_status: str = NOT_REQUESTED
    execution_status: str = NOT_EXECUTED
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)
    model_assisted: bool = False

    def __post_init__(self) -> None:
        _require_value("plan_status", self.plan_status, {PROPOSED})
        _require_value("lifecycle_state", self.lifecycle_state, {PROPOSED})
        _require_value("approval_status", self.approval_status, {NOT_REQUESTED})
        _require_value("execution_status", self.execution_status, {NOT_EXECUTED})
        if self.version < 1:
            raise ValueError("version must be >= 1")
        _require_scope_id("tenant_id", self.tenant_id)
        _require_scope_id("user_id", self.user_id)
        if self.model_assisted:
            raise ValueError("model-assisted planning is disabled for v1 rollout")

    def safe_trace(self) -> dict[str, Any]:
        return {
            "plan_id": _safe_label(self.plan_id),
            "planning_request_id": _safe_label(self.planning_request_id),
            "strategy_id": _safe_label(self.strategy_id),
            "version": self.version,
            "tenant_id_digest": _digest(self.tenant_id or "")[:16],
            "user_id_digest": _digest(self.user_id or "")[:16],
            "reasoning_plan_id": _safe_label(self.reasoning_plan_id),
            "objective": self.objective.safe_trace(),
            "workstream_count": len(self.workstreams),
            "milestone_count": len(self.milestones),
            "step_count": len(self.steps),
            "dependency_count": len(self.dependencies),
            "decision_point_count": len(self.decision_points),
            "risk_count": len(self.risks),
            "mitigation_count": len(self.mitigations),
            "success_measure_count": len(self.success_measures),
            "approval_requirement_count": len(self.approval_requirements),
            "proposed_action_count": len(self.proposed_actions),
            "evidence_reference_count": len(self.evidence_refs),
            "assumption_count": len(self.assumptions),
            "limitation_count": len(self.limitations),
            "confidence": self.confidence,
            "sensitivity": self.sensitivity,
            "lifecycle_state": self.lifecycle_state,
            "plan_status": self.plan_status,
            "approval_status": self.approval_status,
            "execution_status": self.execution_status,
            "model_assisted": self.model_assisted,
        }


@dataclass(frozen=True)
class CandidatePlan(ExecutivePlan):
    candidate_id: str | None = None
    name: str = ""
    time_horizon: str | None = None
    resource_profile: str = "unknown"
    complexity: str = "medium"
    reversibility: str = "partially_reversible"
    evidence_coverage: str = "partial"


@dataclass(frozen=True)
class PlanningSnapshot:
    planning_request_id: str
    status: str
    strategy_id: str | None
    eligible: bool
    reason_code: str
    candidate_plans: tuple[CandidatePlan, ...] = ()
    recommended_plan: ExecutivePlan | None = None
    errors: tuple[PlanningError, ...] = ()
    warnings: tuple[str, ...] = ()
    confidence: str = "unknown"
    latency_ms: int = 0
    approval_status: str = NOT_REQUESTED
    execution_status: str = NOT_EXECUTED
    external_calls_enabled: bool = False
    model_assisted: bool = False

    def safe_trace(self) -> dict[str, Any]:
        return {
            "planning_request_id": _safe_label(self.planning_request_id),
            "status": self.status,
            "strategy_id": self.strategy_id,
            "eligible": self.eligible,
            "reason_code": self.reason_code,
            "candidate_count": len(self.candidate_plans),
            "recommended_plan_id": self.recommended_plan.plan_id
            if self.recommended_plan
            else None,
            "error_count": len(self.errors),
            "warnings": [_safe_label(warning) for warning in self.warnings],
            "confidence": self.confidence,
            "latency_ms": self.latency_ms,
            "approval_status": self.approval_status,
            "execution_status": self.execution_status,
            "external_calls_enabled": self.external_calls_enabled,
            "model_assisted": self.model_assisted,
            "plan_digest": _digest(
                json.dumps(
                    [
                        plan.safe_trace()
                        for plan in self.candidate_plans[
                            : planning_limits().max_candidates
                        ]
                    ],
                    sort_keys=True,
                )
            )[:16],
        }


@dataclass(frozen=True)
class PlanningExecutionResult:
    status: str = "unavailable"
    approval_status: str = NOT_REQUESTED
    execution_status: str = NOT_EXECUTED
    external_calls_enabled: bool = False
    safe_message: str = PLANNING_LIMITATION


@dataclass(frozen=True)
class PlanningStrategy:
    strategy_id: str
    version: str
    description: str
    supported_plan_types: tuple[str, ...]
    deterministic: bool = True
    enabled: bool = True
    lifecycle_state: str = "enabled"
    evidence_required: bool = True
    execution_supported: bool = False
    external_calls_enabled: bool = False
    health: str = "ok"
    risk: str = "low"
    tenant_scope: str = "all"
    user_scope: str = "all"

    def safe_trace(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "description": self.description,
            "supported_plan_types": list(self.supported_plan_types),
            "deterministic": self.deterministic,
            "enabled": self.enabled,
            "lifecycle_state": self.lifecycle_state,
            "evidence_required": self.evidence_required,
            "execution_supported": self.execution_supported,
            "external_calls_enabled": self.external_calls_enabled,
            "health": self.health,
            "risk": self.risk,
            "tenant_scope": self.tenant_scope,
            "user_scope": self.user_scope,
        }


class PlanningRegistry:
    def __init__(self, strategies: Sequence[PlanningStrategy]) -> None:
        self._strategies: dict[str, PlanningStrategy] = {}
        for strategy in strategies:
            self.register(strategy)

    def register(self, strategy: PlanningStrategy) -> None:
        if strategy.strategy_id in self._strategies:
            raise ValueError(f"duplicate planning strategy: {strategy.strategy_id}")
        if strategy.execution_supported or strategy.external_calls_enabled:
            raise ValueError(
                "planning strategies cannot support execution or external calls"
            )
        self._strategies[strategy.strategy_id] = strategy

    def enable(self, strategy_id: str) -> None:
        self._strategies[strategy_id] = replace(
            self.lookup(strategy_id),
            enabled=True,
            lifecycle_state="enabled",
        )

    def disable(self, strategy_id: str) -> None:
        self._strategies[strategy_id] = replace(
            self.lookup(strategy_id),
            enabled=False,
            lifecycle_state="disabled",
        )

    def strategy_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._strategies))

    def lookup(self, strategy_id: str) -> PlanningStrategy:
        try:
            strategy = self._strategies[strategy_id]
        except KeyError as exc:
            raise ValueError(f"unknown planning strategy: {strategy_id}") from exc
        if not strategy.enabled:
            raise ValueError(f"disabled planning strategy: {strategy_id}")
        if strategy.lifecycle_state != "enabled":
            raise ValueError(f"unavailable planning strategy: {strategy_id}")
        if strategy.health != "ok":
            raise ValueError(f"unhealthy planning strategy: {strategy_id}")
        return strategy

    def enabled_strategies(self) -> tuple[PlanningStrategy, ...]:
        return tuple(
            self._strategies[strategy_id]
            for strategy_id in self.strategy_ids()
            if self._strategies[strategy_id].enabled
            and self._strategies[strategy_id].lifecycle_state == "enabled"
            and self._strategies[strategy_id].health == "ok"
        )

    def select(
        self,
        strategy_id: str,
        *,
        tenant_id: str,
        actor_id: str,
        deterministic_only: bool = True,
    ) -> PlanningStrategy:
        strategy = self.lookup(strategy_id)
        _require_scope_id("tenant_id", tenant_id)
        _require_scope_id("actor_id", actor_id)
        if deterministic_only and not strategy.deterministic:
            raise ValueError(f"non-deterministic planning strategy: {strategy_id}")
        return strategy

    def health(self) -> dict[str, Any]:
        return {
            "strategy_count": len(self._strategies),
            "enabled_strategy_count": len(self.enabled_strategies()),
            "health": "ok",
            "external_calls_enabled": False,
        }


@dataclass(frozen=True)
class PlanningLimits:
    max_candidates: int = 3
    max_workstreams: int = 8
    max_milestones: int = 12
    max_steps: int = 30
    max_risks: int = 12
    max_proposed_actions: int = 15
    max_evidence_refs: int = 20
    max_rendered_chars: int = 4_000


@dataclass(frozen=True)
class ExecutivePlanningRequest:
    planning_request_id: str
    correlation_id: str
    tenant_id: str
    actor_id: str
    normalized_user_request: str
    request_classification: str
    reasoning_plan: Mapping[str, Any]
    context_source_counts: Mapping[str, int]
    evidence_refs: tuple[str, ...]
    safety_state: str
    primary_objective: str = ""
    desired_outcome: str = ""
    completion_definition: str = ""
    time_horizon: str | None = None
    scope: str = "request_scoped"
    excluded_scope: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    known_resources: tuple[str, ...] = ()
    known_owners: tuple[str, ...] = ()
    known_dependencies: tuple[str, ...] = ()
    success_measures: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_scope_id("tenant_id", self.tenant_id)
        _require_scope_id("actor_id", self.actor_id)
        if not self.planning_request_id.strip():
            raise ValueError("planning_request_id is required")

    @classmethod
    def from_reasoning_plan(
        cls,
        *,
        reasoning_plan: Any,
        normalized_user_request: str,
        tenant_id: str,
        actor_id: str,
        context_source_counts: Mapping[str, int],
        evidence_refs: tuple[str, ...],
        trace_metadata: Mapping[str, Any],
        safety_state: str | None = None,
    ) -> ExecutivePlanningRequest:
        trace = (
            reasoning_plan.safe_trace()
            if hasattr(reasoning_plan, "safe_trace")
            else dict(reasoning_plan)
        )
        correlation_id = str(trace.get("correlation_id") or "")
        seed = "|".join((
            correlation_id,
            tenant_id,
            actor_id,
            _digest(normalized_user_request)[:16],
        ))
        return cls(
            planning_request_id=f"epr_{_digest(seed)[:16]}",
            correlation_id=correlation_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            normalized_user_request=_safe_text(normalized_user_request, 1_000),
            request_classification=str(trace.get("request_classification") or ""),
            reasoning_plan=trace,
            context_source_counts=dict(context_source_counts),
            evidence_refs=tuple(_safe_label(ref) for ref in evidence_refs)[
                : planning_limits().max_evidence_refs
            ],
            safety_state=safety_state
            or str(trace.get("safety_state") or "normal_non_executing"),
            primary_objective=str(trace.get("user_objective") or "").strip(),
            desired_outcome=_desired_outcome_from_text(normalized_user_request),
            completion_definition=_completion_definition_from_text(
                normalized_user_request
            ),
            constraints=tuple(str(item) for item in trace.get("constraints") or ()),
            unresolved_questions=tuple(
                str(item) for item in trace.get("missing_information") or ()
            ),
            trace_metadata=dict(trace_metadata),
        )


@dataclass(frozen=True)
class PlanningPolicyDecision:
    eligible: bool
    reason_code: str
    safe_message: str


class PlanningPolicy:
    def evaluate(self, request: ExecutivePlanningRequest) -> PlanningPolicyDecision:
        if not is_planning_engine_enabled():
            return PlanningPolicyDecision(
                False,
                "planning_engine_disabled",
                "Executive Planning Engine is disabled.",
            )
        if request.reasoning_plan.get("execution_permitted") is True:
            return PlanningPolicyDecision(
                False,
                "reasoning_plan_not_non_executing",
                "ReasoningPlan cannot permit execution for planning v1.",
            )
        if request.request_classification != "planning_request":
            return PlanningPolicyDecision(
                False,
                "classification_not_planning",
                "Planning is bypassed for this request classification.",
            )
        if str(request.reasoning_plan.get("reasoning_mode")) != "planning_stub":
            return PlanningPolicyDecision(
                False,
                "reasoning_mode_not_planning_stub",
                "Planning requires a safe planning_stub ReasoningPlan.",
            )
        if _contains_command_like_payload(request.normalized_user_request):
            return PlanningPolicyDecision(
                False,
                "unsafe_payload_not_plannable",
                "Unsafe executable payloads cannot become planning content.",
            )
        if not _has_objective(request.normalized_user_request):
            return PlanningPolicyDecision(
                False,
                "objective_missing",
                "A planning objective is required before candidate plans are generated.",
            )
        return PlanningPolicyDecision(
            True,
            "planning_stub_eligible",
            "ReasoningPlan is eligible for deterministic non-executing planning.",
        )


class ExecutivePlanningEngine:
    def __init__(
        self,
        *,
        registry: PlanningRegistry | None = None,
        policy: PlanningPolicy | None = None,
        limits: PlanningLimits | None = None,
    ) -> None:
        self.registry = registry or build_default_planning_registry()
        self.policy = policy or PlanningPolicy()
        self.limits = limits or planning_limits()

    def plan(self, request: ExecutivePlanningRequest) -> PlanningSnapshot:
        started = time.monotonic()
        decision = self.policy.evaluate(request)
        if not decision.eligible:
            return PlanningSnapshot(
                planning_request_id=request.planning_request_id,
                status="not_eligible",
                strategy_id=None,
                eligible=False,
                reason_code=decision.reason_code,
                warnings=(decision.safe_message,),
                latency_ms=_elapsed_ms(started),
            )
        strategy_id = _select_strategy(request.normalized_user_request)
        try:
            strategy = self.registry.select(
                strategy_id,
                tenant_id=request.tenant_id,
                actor_id=request.actor_id,
                deterministic_only=True,
            )
        except ValueError as exc:
            return PlanningSnapshot(
                planning_request_id=request.planning_request_id,
                status="not_eligible",
                strategy_id=strategy_id,
                eligible=False,
                reason_code="strategy_unavailable",
                errors=(
                    PlanningError(
                        "strategy_unavailable",
                        _safe_text(str(exc), 240),
                    ),
                ),
                latency_ms=_elapsed_ms(started),
            )
        candidates = _generate_candidates(request, strategy, self.limits)
        candidates = tuple(candidates[: self.limits.max_candidates])
        evaluated = tuple(_attach_evaluations(candidates, strategy_id))
        errors = tuple(
            error
            for candidate in evaluated
            for error in validate_plan_dependencies(candidate)
            + validate_plan_structure(candidate)
        )
        if errors:
            return PlanningSnapshot(
                planning_request_id=request.planning_request_id,
                status="invalid",
                strategy_id=strategy_id,
                eligible=True,
                reason_code="dependency_validation_failed",
                candidate_plans=evaluated,
                errors=errors,
                confidence="unknown",
                latency_ms=_elapsed_ms(started),
            )
        recommended = max(
            evaluated,
            key=lambda plan: plan.evaluation.total_score if plan.evaluation else 0,
        )
        recommended = _with_recommendation(recommended, evaluated)
        evaluated = tuple(
            recommended if plan.plan_id == recommended.plan_id else plan
            for plan in evaluated
        )
        return PlanningSnapshot(
            planning_request_id=request.planning_request_id,
            status=PROPOSED,
            strategy_id=strategy_id,
            eligible=True,
            reason_code=decision.reason_code,
            candidate_plans=evaluated,
            recommended_plan=recommended,
            confidence=_planning_confidence(request, recommended),
            latency_ms=_elapsed_ms(started),
        )


def build_default_planning_engine() -> ExecutivePlanningEngine:
    return ExecutivePlanningEngine()


def build_default_planning_registry() -> PlanningRegistry:
    return PlanningRegistry((
        PlanningStrategy(
            strategy_id="milestone_plan",
            version="1.0",
            description="Strategic milestone plan with phases, risks, decision points and success measures.",
            supported_plan_types=(
                "strategic",
                "business",
                "architecture",
                "organisational",
            ),
        ),
        PlanningStrategy(
            strategy_id="implementation_plan",
            version="1.0",
            description="Technical implementation plan with discovery, build, validation, rollout and rollback readiness.",
            supported_plan_types=("technical", "process", "rollout", "migration"),
        ),
        PlanningStrategy(
            strategy_id="decision_plan",
            version="1.0",
            description="Option-comparison plan with criteria, evidence needs and recommendation conditions.",
            supported_plan_types=("decision", "comparison", "prioritisation"),
        ),
        PlanningStrategy(
            strategy_id="review_plan",
            version="1.0",
            description="Review plan covering scope, criteria, evidence, findings and decision points.",
            supported_plan_types=("review", "audit", "risk"),
        ),
    ))


def is_planning_engine_enabled() -> bool:
    value = os.getenv("HERMES_PLANNING_ENGINE_ENABLED")
    return True if value is None else _is_truthy_value(value)


def is_planning_registry_enabled() -> bool:
    value = os.getenv("HERMES_PLANNING_REGISTRY_ENABLED")
    return True if value is None else _is_truthy_value(value)


def is_deterministic_planning_enabled() -> bool:
    value = os.getenv("HERMES_DETERMINISTIC_PLANNING_ENABLED")
    return True if value is None else _is_truthy_value(value)


def is_model_assisted_planning_enabled() -> bool:
    return _is_truthy_value(os.getenv("HERMES_PLANNING_MODEL_ASSISTED_ENABLED"))


def is_candidate_evaluation_enabled() -> bool:
    value = os.getenv("HERMES_PLANNING_CANDIDATE_EVALUATION_ENABLED")
    return True if value is None else _is_truthy_value(value)


def is_proposed_action_generation_enabled() -> bool:
    value = os.getenv("HERMES_PLANNING_PROPOSED_ACTION_GENERATION_ENABLED")
    return True if value is None else _is_truthy_value(value)


def build_planning_status() -> dict[str, Any]:
    registry = build_default_planning_registry()
    return {
        "enabled": is_planning_engine_enabled(),
        "registry_enabled": is_planning_registry_enabled(),
        "deterministic_planning_enabled": is_deterministic_planning_enabled(),
        "model_assisted_planning_enabled": is_model_assisted_planning_enabled(),
        "candidate_evaluation_enabled": is_candidate_evaluation_enabled(),
        "proposed_action_generation_enabled": is_proposed_action_generation_enabled(),
        "approval_engine_enabled": False,
        "approval_recording_available": False,
        "execution_engine_enabled": False,
        "calendar_authorisation_enabled": False,
        "calendar_live_reads_enabled": False,
        "calendar_writes_enabled": False,
        "mcp_enabled": False,
        "external_mutations_enabled": False,
        "live_execution_enabled": False,
        "external_calls_enabled": False,
        "execution_boundary": NOT_EXECUTED,
        "execution_status": NOT_EXECUTED,
        "approval_status": NOT_REQUESTED,
        "strategy_count": len(registry.strategy_ids()),
        "enabled_strategy_count": len(registry.enabled_strategies()),
        "storage_mode": "request_scoped",
        "last_status": "ok",
        "last_plan_status": PROPOSED,
        "last_error": None,
        "last_candidate_count": 0,
        "last_step_count": 0,
        "last_risk_count": 0,
        "last_approval_requirement_count": 0,
        "last_proposed_action_count": 0,
        "safe_digest": _digest(json.dumps(registry.health(), sort_keys=True))[:16],
        "redacted": True,
    }


def render_planning_snapshot_for_prompt(snapshot: PlanningSnapshot) -> str:
    lines = [
        "EXECUTIVE PLANNING SNAPSHOT",
        f"Planning status: {snapshot.status}",
        f"Strategy: {snapshot.strategy_id or 'none'}",
        f"Approval status: {snapshot.approval_status}",
        f"Execution status: {snapshot.execution_status}",
        "External execution: unavailable/not_executed",
    ]
    if snapshot.recommended_plan is None:
        lines.append(
            f"Planning limitation: {', '.join(snapshot.warnings) or snapshot.reason_code}"
        )
        return "\n".join(lines)
    plan = snapshot.recommended_plan
    lines.extend((
        "Planning Objective:",
        f"- {plan.objective.summary}",
        "Recommended Proposed Plan:",
    ))
    for milestone in plan.milestones[:4]:
        lines.append(
            f"- {milestone.title} ({milestone.status}, {milestone.execution_status})"
        )
    if plan.steps:
        lines.append("Proposed Steps:")
        for step in plan.steps[:8]:
            lines.append(
                f"- {step.sequence}. {step.title} [{step.status}/{step.execution_status}]"
            )
    if plan.risks:
        lines.append("Risks and Mitigations:")
        for risk in plan.risks[:4]:
            mitigation = next(
                (
                    item.summary
                    for item in plan.mitigations
                    if item.risk_id == risk.risk_id
                ),
                "Mitigation to be refined before approval.",
            )
            lines.append(f"- {risk.summary}; mitigation: {mitigation}")
    if plan.decision_points:
        lines.append("Decision Points:")
        for decision in plan.decision_points[:4]:
            lines.append(f"- {decision.title} ({decision.status})")
    if plan.proposed_actions:
        lines.append("Proposed Actions:")
        for action in plan.proposed_actions[:4]:
            lines.append(
                f"- {action.action_type}: declarative only; approval={action.approval_status}; execution={action.execution_status}"
            )
    lines.extend((
        "Approval Boundary:",
        "- This plan is not approved. No user request alone is approval.",
        "Limitations:",
        f"- {PLANNING_LIMITATION}",
    ))
    rendered = "\n".join(lines)
    if len(rendered) <= planning_limits().max_rendered_chars:
        return rendered
    return (
        rendered[: planning_limits().max_rendered_chars - 24].rstrip()
        + "\n[planning truncated]"
    )


def validate_plan_dependencies(plan: ExecutivePlan) -> tuple[PlanningError, ...]:
    element_ids = {step.step_id for step in plan.steps}
    element_ids.update(milestone.milestone_id for milestone in plan.milestones)
    errors: list[PlanningError] = []
    for dependency in plan.dependencies:
        if (
            dependency.predecessor_id not in element_ids
            or dependency.successor_id not in element_ids
        ):
            errors.append(
                PlanningError(
                    "missing_dependency_reference",
                    "A dependency references a missing plan element.",
                )
            )
            return tuple(errors)
    graph: dict[str, set[str]] = {element_id: set() for element_id in element_ids}
    for dependency in plan.dependencies:
        graph.setdefault(dependency.predecessor_id, set()).add(dependency.successor_id)
    if _has_cycle(graph):
        return (
            PlanningError(
                "circular_dependency",
                "A circular dependency was detected in the proposed plan.",
            ),
        )
    sequences = [step.sequence for step in plan.steps]
    if len(sequences) != len(set(sequences)):
        return (
            PlanningError(
                "duplicate_step_sequence",
                "Two proposed steps use the same sequence number.",
            ),
        )
    for step in plan.steps:
        if step.execution_status != NOT_EXECUTED or step.status != PROPOSED:
            return (
                PlanningError(
                    "executable_step_state",
                    "A step attempted to leave the proposed/not_executed state.",
                ),
            )
    return ()


def validate_plan_structure(plan: ExecutivePlan) -> tuple[PlanningError, ...]:
    if plan.plan_status != PROPOSED or plan.lifecycle_state != PROPOSED:
        return (
            PlanningError(
                "invalid_lifecycle_state",
                "A v1 plan attempted to leave the proposed lifecycle.",
            ),
        )
    if plan.approval_status != NOT_REQUESTED:
        return (
            PlanningError(
                "approval_boundary_violation",
                "A v1 plan attempted to request or record approval.",
            ),
        )
    if plan.execution_status != NOT_EXECUTED:
        return (
            PlanningError(
                "execution_boundary_violation",
                "A v1 plan attempted to change execution state.",
            ),
        )
    if not plan.tenant_id or not plan.user_id:
        return (
            PlanningError(
                "cross_tenant_scope",
                "A v1 plan must carry tenant and user scope.",
            ),
        )
    for milestone in plan.milestones:
        if not milestone.completion_condition.strip():
            return (
                PlanningError(
                    "milestone_incomplete",
                    "A milestone is missing its completion condition.",
                ),
            )
    approval_ids = {
        requirement.approval_requirement_id
        for requirement in plan.approval_requirements
        if requirement.approval_status == NOT_REQUESTED
        and requirement.status == NOT_REQUESTED
    }
    for action in plan.proposed_actions:
        if action.approval_status != NOT_REQUESTED:
            return (
                PlanningError(
                    "approval_boundary_violation",
                    "A proposed action attempted to advance approval state.",
                ),
            )
        if action.execution_status != NOT_EXECUTED:
            return (
                PlanningError(
                    "execution_boundary_violation",
                    "A proposed action attempted to advance execution state.",
                ),
            )
        if action.adapter_id or action.external_payload:
            return (
                PlanningError(
                    "execution_boundary_violation",
                    "A proposed action attempted to bind an adapter or payload.",
                ),
            )
        if (
            action.approval_required
            and action.approval_requirement_id not in approval_ids
        ):
            return (
                PlanningError(
                    "approval_boundary_violation",
                    "A future external action is missing a not_requested approval requirement.",
                ),
            )
    return ()


def _generate_candidates(
    request: ExecutivePlanningRequest,
    strategy: PlanningStrategy,
    limits: PlanningLimits,
) -> tuple[CandidatePlan, ...]:
    variants = _candidate_variants(
        request.normalized_user_request, strategy.strategy_id
    )
    candidates = [
        _build_candidate_plan(request, strategy, variant, index + 1, limits)
        for index, variant in enumerate(variants[: limits.max_candidates])
    ]
    return tuple(candidates)


def _build_candidate_plan(
    request: ExecutivePlanningRequest,
    strategy: PlanningStrategy,
    variant: str,
    index: int,
    limits: PlanningLimits,
) -> CandidatePlan:
    base_id = _digest(
        json.dumps(
            {
                "request": request.planning_request_id,
                "strategy": strategy.strategy_id,
                "variant": variant,
                "index": index,
            },
            sort_keys=True,
        )
    )[:12]
    plan_id = f"plan_{base_id}"
    workstream = PlanWorkstream(
        workstream_id=f"ws_{base_id}_1",
        title=_strategy_workstream_title(strategy.strategy_id, variant),
        objective=_objective_summary(request, variant),
        sequence=1,
        success_measure_ids=(f"sm_{base_id}_1",),
    )
    milestones = tuple(
        PlanMilestone(
            milestone_id=f"ms_{base_id}_{i}",
            title=title,
            success_measure_ids=(f"sm_{base_id}_{i}",),
            sequence=i,
            completion_condition="Named completion evidence is ready for human review.",
            evidence_refs=request.evidence_refs,
        )
        for i, title in enumerate(
            _milestone_titles(strategy.strategy_id, variant), start=1
        )
    )[: limits.max_milestones]
    success = tuple(
        PlanSuccessMeasure(
            measure_id=f"sm_{base_id}_{i}",
            summary=f"Milestone {i} has an observable completion signal.",
            target_state="Evidence-backed milestone decision or deliverable is ready.",
        )
        for i in range(1, len(milestones) + 1)
    )
    steps = tuple(
        PlanStep(
            step_id=f"step_{base_id}_{i}",
            title=title,
            sequence=i,
            workstream_id=workstream.workstream_id,
            milestone_id=milestones[min(i - 1, len(milestones) - 1)].milestone_id
            if milestones
            else None,
            description="Proposed planning work only; not an executable instruction.",
            step_type=strategy.strategy_id.replace("_plan", ""),
            dependencies=tuple(),
            expected_output="Decision-ready proposed planning artefact.",
            success_condition="Human reviewer can accept, reject or ask to revise the proposal.",
            approval_requirement="future_approval_required_before_execution"
            if _is_external_mutation_text(request.normalized_user_request)
            else None,
            capability_requirements=(_capability_requirement_for_title(title),),
            evidence_refs=request.evidence_refs,
            assumptions=("Operational details remain unconfirmed.",),
            risks=("Execution must not begin from this proposal.",),
        )
        for i, title in enumerate(_step_titles(strategy.strategy_id, variant), start=1)
    )[: limits.max_steps]
    dependencies = tuple(
        PlanDependency(
            dependency_id=f"dep_{base_id}_{i}",
            predecessor_id=steps[i - 1].step_id,
            successor_id=steps[i].step_id,
        )
        for i in range(1, len(steps))
    )
    decision_points = (
        PlanDecisionPoint(
            decision_point_id=f"dp_{base_id}_1",
            title="Authorised human review before approval or execution is considered.",
            required_before_step_id=steps[-1].step_id if steps else None,
            evidence_required=("approval_boundary_evidence",),
            risk_class="medium",
        ),
    )
    risks = tuple(
        PlanRisk(
            risk_id=f"risk_{base_id}_{i}",
            summary=summary,
            likelihood="unknown",
            impact="medium",
        )
        for i, summary in enumerate(_risk_summaries(strategy.strategy_id), start=1)
    )[: limits.max_risks]
    mitigations = tuple(
        PlanMitigation(
            mitigation_id=f"mit_{base_id}_{i}",
            risk_id=risk.risk_id,
            summary=_mitigation_for_risk(risk.summary),
        )
        for i, risk in enumerate(risks, start=1)
    )
    proposed_actions, approvals = _proposed_actions_for_request(request, base_id)
    if proposed_actions and steps:
        first = steps[0]
        steps = (
            PlanStep(
                step_id=first.step_id,
                title=first.title,
                sequence=first.sequence,
                workstream_id=first.workstream_id,
                milestone_id=first.milestone_id,
                description=first.description,
                owner_requirement_ids=first.owner_requirement_ids,
                resource_requirement_ids=first.resource_requirement_ids,
                dependency_ids=first.dependency_ids,
                approval_requirement_ids=tuple(
                    item.approval_requirement_id for item in approvals
                ),
                proposed_action_reference_ids=tuple(
                    item.proposed_action_reference_id for item in proposed_actions
                ),
                evidence_refs=first.evidence_refs,
            ),
            *steps[1:],
        )
    evidence_refs = tuple(
        PlanningEvidenceReference(
            evidence_id=ref,
            source_category=_source_category_for_ref(
                ref, request.context_source_counts
            ),
        )
        for ref in request.evidence_refs[: limits.max_evidence_refs]
    )
    return CandidatePlan(
        plan_id=plan_id,
        planning_request_id=request.planning_request_id,
        strategy_id=strategy.strategy_id,
        tenant_id=request.tenant_id,
        user_id=request.actor_id,
        request_id=request.correlation_id,
        reasoning_plan_id=str(request.reasoning_plan.get("plan_id") or ""),
        concise_summary=f"Proposed {strategy.strategy_id} using {_safe_label(variant)} route.",
        scope=request.scope,
        objective=PlanObjective(
            objective_id=f"objective_{base_id}",
            summary=_objective_summary(request, variant),
            desired_outcome=request.desired_outcome,
            completion_definition=request.completion_definition,
            time_horizon=request.time_horizon,
            scope=request.scope,
            excluded_scope=request.excluded_scope,
            evidence_refs=request.evidence_refs,
        ),
        constraints=(
            PlanConstraint(
                constraint_id=f"constraint_{base_id}_1",
                summary="No approvals or external execution are available in Planning Engine v1.",
                constraint_type="safety",
            ),
            PlanConstraint(
                constraint_id=f"constraint_{base_id}_2",
                summary="Use only bounded Hermes context, intelligence and reasoning evidence.",
                constraint_type="evidence",
            ),
        ),
        assumptions=(
            PlanAssumption(
                assumption_id=f"assumption_{base_id}_1",
                summary="Missing operational details must be confirmed before approval.",
            ),
        ),
        workstreams=(workstream,),
        milestones=milestones,
        steps=steps,
        dependencies=dependencies,
        decision_points=decision_points,
        risks=risks,
        mitigations=mitigations,
        success_measures=success,
        resource_requirements=(
            PlanResourceRequirement(
                requirement_id=f"res_{base_id}_1",
                summary="Required resources are unconfirmed and must be validated before approval.",
                resource_type="team_capacity",
            ),
        ),
        owner_requirements=(
            PlanOwnerRequirement(
                requirement_id=f"owner_{base_id}_1",
                summary="A responsible owner must be named before approval.",
                required_role="accountable_owner",
            ),
        ),
        evidence_refs=evidence_refs,
        approval_requirements=approvals,
        proposed_actions=proposed_actions[: limits.max_proposed_actions],
        confidence=_planning_confidence_seed(request),
        candidate_id=plan_id,
        name=_strategy_workstream_title(strategy.strategy_id, variant),
        time_horizon=request.time_horizon,
        resource_profile="unconfirmed",
        complexity="medium",
        evidence_coverage="partial" if request.evidence_refs else "limited",
    )


def _attach_evaluations(
    candidates: tuple[CandidatePlan, ...], strategy_id: str
) -> list[CandidatePlan]:
    criteria = _evaluation_criteria(strategy_id)
    evaluated: list[CandidatePlan] = []
    for index, candidate in enumerate(candidates):
        ratings = {
            criterion.criterion_id: max(1, min(5, 5 - index)) for criterion in criteria
        }
        rationales = {
            criterion.criterion_id: criterion.rationale for criterion in criteria
        }
        total = sum(
            ratings[criterion.criterion_id] * criterion.weight for criterion in criteria
        )
        evaluated.append(
            cast(
                CandidatePlan,
                _replace_plan(
                    candidate,
                    evaluation=PlanEvaluation(
                        evaluation_id=f"eval_{candidate.plan_id}",
                        candidate_plan_id=candidate.plan_id,
                        criterion_ratings=ratings,
                        criterion_rationales=rationales,
                        total_score=total,
                        summary="Transparent deterministic evaluation from bounded criteria.",
                        criteria=criteria,
                    ),
                ),
            )
        )
    return evaluated


def _with_recommendation(
    recommended: CandidatePlan,
    candidates: tuple[CandidatePlan, ...],
) -> CandidatePlan:
    alternates = tuple(
        f"Consider {plan.plan_id} if its tradeoffs become preferable."
        for plan in candidates
        if plan.plan_id != recommended.plan_id
    )
    return cast(
        CandidatePlan,
        _replace_plan(
            recommended,
            recommendation=PlanRecommendation(
                recommended_plan_id=recommended.plan_id,
                rationale=(
                    "Recommended as the strongest proposed route from the deterministic "
                    "evaluation. This plan is not approved or executed."
                ),
                tradeoffs=(
                    "More detail will be required before approval.",
                    "Owners, dates and resources remain proposal-level unless supplied as evidence.",
                ),
                alternate_conditions=alternates,
                unresolved_assumptions=tuple(
                    item.summary for item in recommended.assumptions
                ),
                approval_status=NOT_REQUESTED,
                execution_status=NOT_EXECUTED,
            ),
            recommended_candidate_id=recommended.plan_id,
        ),
    )


def _replace_plan(plan: ExecutivePlan, **changes: Any) -> ExecutivePlan:
    return replace(plan, **changes)


def _select_strategy(text: str) -> str:
    folded = text.casefold()
    if _is_external_mutation_text(folded):
        return "implementation_plan"
    if _contains_any(
        folded,
        ("implement", "deployment", "migration", "technical", "rollout", "build"),
    ):
        return "implementation_plan"
    if _contains_any(
        folded, ("decide", "decision", "compare", "versus", " vs ", " or ")
    ):
        return "decision_plan"
    if _contains_any(folded, ("review", "audit", "assess")):
        return "review_plan"
    return "milestone_plan"


def _candidate_variants(text: str, strategy_id: str) -> tuple[str, ...]:
    if strategy_id == "decision_plan":
        options = _extract_options(text)
        if len(options) >= 2:
            return tuple(options[:3])
    if strategy_id == "implementation_plan":
        return ("phased_delivery", "minimal_viable_rollout")
    if strategy_id == "review_plan":
        return ("evidence_first_review",)
    return ("milestone_first", "risk_first")


def _extract_options(text: str) -> list[str]:
    clean = _safe_text(text, 240)
    if " or " in clean.casefold():
        return [
            part.strip(" ?.")
            for part in re.split(r"\bor\b", clean, maxsplit=2, flags=re.I)
            if part.strip()
        ]
    return []


def _objective_summary(request: ExecutivePlanningRequest, variant: str) -> str:
    objective = str(request.reasoning_plan.get("user_objective") or "").strip()
    if not objective:
        objective = "Create a governed non-executing plan for the user request."
    return f"{objective} Variant: {_safe_label(variant)}."


def _strategy_workstream_title(strategy_id: str, variant: str) -> str:
    titles = {
        "milestone_plan": "Milestone shaping and governance",
        "implementation_plan": "Implementation readiness and validation",
        "decision_plan": "Decision evidence and option evaluation",
        "review_plan": "Review scope, evidence and findings",
    }
    return f"{titles.get(strategy_id, 'Executive planning')} ({_safe_label(variant)})"


def _milestone_titles(strategy_id: str, variant: str) -> tuple[str, ...]:
    if strategy_id == "implementation_plan":
        return (
            "Discovery and constraints confirmed",
            "Design and safety boundaries accepted",
            "Build validated in controlled environment",
            "Rollout and rollback readiness reviewed",
        )
    if strategy_id == "decision_plan":
        return (
            f"Evidence gathered for {_safe_label(variant)}",
            "Decision criteria reviewed",
            "Recommendation conditions documented",
        )
    if strategy_id == "review_plan":
        return (
            "Scope and evidence inventory completed",
            "Findings and risks reviewed",
            "Decision points prepared",
        )
    return (
        "Outcome and constraints clarified",
        "Candidate route selected for review",
        "Risks, dependencies and success measures prepared",
    )


def _step_titles(strategy_id: str, variant: str) -> tuple[str, ...]:
    if strategy_id == "implementation_plan":
        return (
            "Confirm scope, constraints and non-execution boundary",
            "Design proposed implementation sequence",
            "Identify validation and rollback checks",
            "Prepare approval-ready summary without executing it",
        )
    if strategy_id == "decision_plan":
        return (
            f"Define the option represented by {_safe_label(variant)}",
            "Map evidence, assumptions and missing information",
            "Apply evaluation criteria",
            "Prepare a recommendation for human review",
        )
    if strategy_id == "review_plan":
        return (
            "Confirm review scope and evidence sources",
            "Assess findings against criteria",
            "Identify risks and unresolved decisions",
            "Prepare review recommendation for human review",
        )
    return (
        "Clarify the milestone outcome and constraints",
        "Sequence the proposed workstreams",
        "Identify dependencies, risks and mitigations",
        "Define success measures and approval gates",
    )


def _risk_summaries(strategy_id: str) -> tuple[str, ...]:
    common = (
        "Critical evidence may be missing or stale.",
        "The proposal may imply work before authorised approval exists.",
    )
    if strategy_id == "implementation_plan":
        return common + ("Deployment readiness could be incomplete.",)
    if strategy_id == "decision_plan":
        return common + ("Options may not be equally evidenced.",)
    return common


def _mitigation_for_risk(summary: str) -> str:
    if "approval" in summary.casefold():
        return "Keep the plan proposed/not_requested/not_executed until a future Approval boundary exists."
    return "Record the limitation and require confirmation before approval."


def _evaluation_criteria(strategy_id: str) -> tuple[PlanEvaluationCriterion, ...]:
    return (
        PlanEvaluationCriterion(
            criterion_id="evidence_fit",
            title="Evidence fit",
            weight=3,
            rationale=f"Candidate is evaluated against available evidence for {strategy_id}.",
        ),
        PlanEvaluationCriterion(
            criterion_id="safety_boundary",
            title="Safety boundary",
            weight=3,
            rationale="Candidate must preserve not_requested/not_executed terminal states.",
        ),
        PlanEvaluationCriterion(
            criterion_id="sequence_clarity",
            title="Sequence clarity",
            weight=2,
            rationale="Candidate should expose dependencies and decision points clearly.",
        ),
    )


def _proposed_actions_for_request(
    request: ExecutivePlanningRequest,
    base_id: str,
) -> tuple[tuple[ProposedActionReference, ...], tuple[ApprovalRequirement, ...]]:
    if not is_proposed_action_generation_enabled():
        return (), ()
    text = request.normalized_user_request.casefold()
    action_types: list[str] = []
    if "clickup" in text or "task" in text:
        action_types.append("clickup_task_creation_proposal")
    if "email" in text or "gmail" in text:
        action_types.append("email_message_proposal")
    if "calendar" in text or "meeting" in text or "schedule" in text:
        action_types.append("calendar_event_proposal")
    if "whatsapp" in text:
        action_types.append("whatsapp_message_proposal")
    if "slack" in text:
        action_types.append("slack_message_proposal")
    approvals: list[ApprovalRequirement] = []
    actions: list[ProposedActionReference] = []
    for index, action_type in enumerate(action_types, start=1):
        approval_id = f"approval_{base_id}_{index}"
        approvals.append(
            ApprovalRequirement(
                approval_requirement_id=approval_id,
                summary=f"Authorised human approval required before {action_type} can be considered.",
                approval_class="external_mutation_authorisation",
                reason="Planning v1 may describe this future action but cannot approve or execute it.",
                required_before_capability_ids=(action_type,),
                evidence_summary="Requires explicit future Approval boundary evidence.",
                risk_class="high"
                if action_type.startswith(("email", "calendar", "clickup"))
                else "medium",
            )
        )
        actions.append(
            ProposedActionReference(
                proposed_action_reference_id=f"pa_{base_id}_{index}",
                action_type=action_type,
                summary=f"Declarative reference for future {action_type}; no adapter or payload is attached.",
                capability_id=action_type,
                external_system=_external_system_for_action_type(action_type),
                risk_class="high"
                if action_type.startswith(("email", "calendar", "clickup"))
                else "medium",
                reversibility="unknown_until_future_execution_design",
                approval_requirement_id=approval_id,
                payload_schema_reference="future_approval_execution_contract",
                payload_preview_safe={
                    "description_only": True,
                    "contains_live_payload": False,
                },
                evidence_references=request.evidence_refs,
            )
        )
    return tuple(actions), tuple(approvals)


def _planning_confidence(request: ExecutivePlanningRequest, plan: ExecutivePlan) -> str:
    if not request.evidence_refs:
        return "assumed"
    if plan.assumptions:
        return "derived"
    return "known"


def _planning_confidence_seed(request: ExecutivePlanningRequest) -> str:
    if not request.evidence_refs:
        return "assumed"
    if request.unresolved_questions:
        return "derived"
    return "known"


def _desired_outcome_from_text(text: str) -> str:
    folded = text.casefold()
    if _contains_any(folded, ("decide", "decision", "compare", " or ")):
        return "A decision-ready comparison with evidence gaps and tradeoffs."
    if _contains_any(folded, ("implement", "build", "rollout", "migration")):
        return "An approval-ready implementation proposal with validation gates."
    if _contains_any(folded, ("review", "audit", "assess")):
        return "A bounded review sequence with findings categories and decision points."
    return "A proposed milestone route with assumptions, risks and success measures."


def _completion_definition_from_text(text: str) -> str:
    folded = text.casefold()
    if _contains_any(folded, ("seven-day", "7-day", "week")):
        return "Seven-day proposal is ready for owner review."
    if _contains_any(folded, ("tomorrow", "today")):
        return "Near-term proposal is ready with unavailable live-action caveats."
    return "Candidate plan and recommendation are ready for human review."


def _capability_requirement_for_title(title: str) -> str:
    folded = title.casefold()
    if "approval" in folded:
        return "future_approval_boundary"
    if "validation" in folded or "review" in folded:
        return "human_review"
    return "planning_only"


def _external_system_for_action_type(action_type: str) -> str | None:
    if action_type.startswith("clickup"):
        return "clickup"
    if action_type.startswith("email"):
        return "email"
    if action_type.startswith("calendar"):
        return "google_calendar"
    if action_type.startswith("whatsapp"):
        return "whatsapp"
    if action_type.startswith("slack"):
        return "slack"
    return None


def _source_category_for_ref(ref: str, counts: Mapping[str, int]) -> str:
    del ref
    for name, count in sorted(counts.items()):
        if int(count or 0) > 0:
            return _safe_label(name)
    return "current_request_metadata"


def _is_external_mutation_text(text: str) -> bool:
    folded = text.casefold()
    return bool(
        re.search(
            r"\b(send|create|schedule|book|modify|delete|update)\b.+\b(email|message|gmail|calendar|meeting|event|clickup|task|whatsapp|slack|crm|webhook)\b",
            folded,
        )
    )


def _allows_non_executing_plan_language(text: str) -> bool:
    folded = text.casefold()
    return _contains_any(
        folded,
        (
            "plan how",
            "would",
            "proposal",
            "proposed",
            "do not execute",
            "without executing",
        ),
    )


def _has_objective(text: str) -> bool:
    folded = text.casefold().strip()
    return bool(folded) and not folded in {"plan", "make a plan"}


def _contains_command_like_payload(value: str) -> bool:
    folded = value.casefold()
    return _contains_any(
        folded,
        ("rm -rf", "curl ", "os.system", "subprocess", "popen", "| sh", "bash -c"),
    )


def _has_cycle(graph: Mapping[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, set()):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def planning_limits() -> PlanningLimits:
    return PlanningLimits()


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _require_value(field_name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}")


def _require_scope_id(field_name: str, value: str | None) -> None:
    if not str(value or "").strip():
        raise ValueError(f"{field_name} is required")


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _safe_label(value: str | None) -> str:
    text = " ".join(str(value or "").split())
    return re.sub(
        r"(?i)(api[_-]?key|token|secret|password)=\S+", r"\1=[REDACTED]", text
    )[:180]


def _safe_text(value: str, limit: int) -> str:
    return _safe_label(value)[:limit]


def _is_truthy_value(value: str | None) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
