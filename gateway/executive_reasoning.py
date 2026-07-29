"""Deterministic Executive Reasoning Engine for Hermes.

The engine creates explicit reasoning and response plans before the LLM call.
It does not call integrations, load credentials, execute skills, invoke tools,
or authorise external actions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import os
import re
from typing import Any

from utils import is_truthy_value


class ConfidenceLevel(StrEnum):
    KNOWN = "known"
    DERIVED = "derived"
    ASSUMED = "assumed"
    UNAVAILABLE = "unavailable"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReasoningMode:
    mode_id: str
    description: str
    expected_structure: tuple[str, ...]


class ReasoningModeRegistry:
    def __init__(self, modes: tuple[ReasoningMode, ...]) -> None:
        self._modes = {mode.mode_id: mode for mode in modes}

    def mode_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._modes))

    def lookup(self, mode_id: str) -> ReasoningMode:
        try:
            return self._modes[mode_id]
        except KeyError as exc:
            raise ValueError(f"unknown reasoning mode: {mode_id}") from exc


@dataclass(frozen=True)
class EvidenceNeed:
    evidence_type: str
    source_category: str
    required: bool
    available: bool
    evidence_refs: tuple[str, ...] = ()
    limitation: str | None = None

    def safe_trace(self) -> dict[str, Any]:
        return {
            "evidence_type": _safe_label(self.evidence_type),
            "source_category": _safe_label(self.source_category),
            "required": self.required,
            "available": self.available,
            "evidence_refs": [_safe_label(ref) for ref in self.evidence_refs],
            "limitation": _safe_label(self.limitation) if self.limitation else None,
        }


@dataclass(frozen=True)
class ReasoningPlan:
    plan_id: str
    correlation_id: str
    request_classification: str
    reasoning_mode: str
    user_objective: str
    sub_questions: tuple[str, ...]
    evidence_needs: tuple[EvidenceNeed, ...]
    confidence_by_claim: Mapping[str, ConfidenceLevel]
    missing_information: tuple[str, ...]
    selected_skills: tuple[str, ...]
    selected_provider: str
    safety_state: str
    constraints: tuple[str, ...] = ()
    clarification_needed: bool = False
    external_calls_enabled: bool = False
    skill_execution: str = "selected_not_executed"
    execution_required: bool = False
    execution_permitted: bool = False

    def safe_trace(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "correlation_id": self.correlation_id,
            "request_classification": self.request_classification,
            "reasoning_mode": self.reasoning_mode,
            "user_objective_digest": _digest(self.user_objective)[:16],
            "sub_question_count": len(self.sub_questions),
            "evidence_needs": [need.safe_trace() for need in self.evidence_needs],
            "confidence_by_claim": {
                _safe_label(claim): level.value
                for claim, level in sorted(self.confidence_by_claim.items())
            },
            "missing_information": [
                _safe_label(item) for item in self.missing_information
            ],
            "selected_skills": list(self.selected_skills),
            "selected_provider": self.selected_provider,
            "safety_state": self.safety_state,
            "constraints": [_safe_label(item) for item in self.constraints],
            "clarification_needed": self.clarification_needed,
            "external_calls_enabled": self.external_calls_enabled,
            "skill_execution": self.skill_execution,
            "execution_required": self.execution_required,
            "execution_permitted": self.execution_permitted,
        }


@dataclass(frozen=True)
class ResponsePlan:
    plan_id: str
    correlation_id: str
    response_goal: str
    evidence_summary: tuple[str, ...]
    confidence_by_claim: Mapping[str, ConfidenceLevel]
    reasoning_mode: str
    selected_skills: tuple[str, ...]
    selected_model: str
    expected_structure: tuple[str, ...]
    limitations: tuple[str, ...]
    safety_state: str
    clarification_needed: bool
    execution_required: bool = False
    execution_permitted: bool = False

    @classmethod
    def from_reasoning_plan(cls, plan: ReasoningPlan) -> ResponsePlan:
        return cls(
            plan_id=f"response_{plan.plan_id}",
            correlation_id=plan.correlation_id,
            response_goal=plan.user_objective,
            evidence_summary=tuple(
                f"{need.source_category}:{'available' if need.available else 'missing'}"
                for need in plan.evidence_needs
            ),
            confidence_by_claim=dict(plan.confidence_by_claim),
            reasoning_mode=plan.reasoning_mode,
            selected_skills=plan.selected_skills,
            selected_model=plan.selected_provider,
            expected_structure=_expected_structure_for_mode(plan.reasoning_mode),
            limitations=plan.missing_information,
            safety_state=plan.safety_state,
            clarification_needed=plan.clarification_needed,
            execution_required=False,
            execution_permitted=False,
        )

    def safe_trace(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "correlation_id": self.correlation_id,
            "response_goal_digest": _digest(self.response_goal)[:16],
            "evidence_summary": [_safe_label(item) for item in self.evidence_summary],
            "confidence_by_claim": {
                _safe_label(claim): level.value
                for claim, level in sorted(self.confidence_by_claim.items())
            },
            "reasoning_mode": self.reasoning_mode,
            "selected_skills": list(self.selected_skills),
            "selected_model": self.selected_model,
            "expected_structure": list(self.expected_structure),
            "limitations": [_safe_label(item) for item in self.limitations],
            "safety_state": self.safety_state,
            "clarification_needed": self.clarification_needed,
            "execution_required": self.execution_required,
            "execution_permitted": self.execution_permitted,
        }


@dataclass(frozen=True)
class ReasoningPlanningRequest:
    correlation_id: str
    tenant_id: str
    actor_id: str
    normalized_user_request: str
    request_classification: str
    context_source_counts: Mapping[str, int]
    evidence_refs: tuple[str, ...]
    safety_state: str
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutiveReasoningResult:
    reasoning_plan: ReasoningPlan
    response_plan: ResponsePlan


class ExecutiveReasoningEngine:
    def __init__(self, *, registry: ReasoningModeRegistry | None = None) -> None:
        self.registry = registry or build_default_reasoning_mode_registry()

    def plan(self, request: ReasoningPlanningRequest) -> ReasoningPlan:
        mode = _select_reasoning_mode(request)
        self.registry.lookup(mode)
        evidence_needs = _plan_evidence(request)
        missing = tuple(
            need.limitation
            for need in evidence_needs
            if not need.available and need.limitation
        )
        confidence = _confidence_by_claim(request, evidence_needs)
        constraints = _constraints_for_request(request, evidence_needs)
        selected_skills = _select_skills(request)
        selected_provider = _select_provider(mode, request)
        return ReasoningPlan(
            plan_id=f"rp_{_digest(_stable_seed(request, mode))[:16]}",
            correlation_id=request.correlation_id,
            request_classification=request.request_classification,
            reasoning_mode=mode,
            user_objective=_objective_for_request(request),
            sub_questions=_sub_questions_for_request(request),
            evidence_needs=evidence_needs,
            confidence_by_claim=confidence,
            missing_information=missing,
            selected_skills=selected_skills,
            selected_provider=selected_provider,
            safety_state=request.safety_state,
            constraints=constraints,
            clarification_needed=_clarification_needed(request, evidence_needs),
            external_calls_enabled=False,
            skill_execution="selected_not_executed",
            execution_required=False,
            execution_permitted=False,
        )

    def prepare(self, request: ReasoningPlanningRequest) -> ExecutiveReasoningResult:
        reasoning_plan = self.plan(request)
        return ExecutiveReasoningResult(
            reasoning_plan=reasoning_plan,
            response_plan=ResponsePlan.from_reasoning_plan(reasoning_plan),
        )


def build_default_reasoning_mode_registry() -> ReasoningModeRegistry:
    return ReasoningModeRegistry(
        modes=(
            ReasoningMode(
                "direct_answer", "Answer directly and concisely.", ("answer",)
            ),
            ReasoningMode(
                "executive_summary",
                "Summarise executive state with priorities and caveats.",
                ("summary", "priorities", "limitations"),
            ),
            ReasoningMode(
                "executive_brief",
                "Produce a brief-style status view.",
                ("brief", "evidence", "next_actions"),
            ),
            ReasoningMode(
                "analysis",
                "Analyse a situation with explicit knowns and unknowns.",
                ("analysis", "knowns", "unknowns"),
            ),
            ReasoningMode(
                "comparison",
                "Compare options and recommend a path.",
                ("options", "recommendation", "tradeoffs"),
            ),
            ReasoningMode(
                "planning_stub",
                "Create a non-executing planning outline.",
                ("goal", "steps", "risks"),
            ),
            ReasoningMode(
                "review",
                "Review supplied material and identify issues.",
                ("findings", "risks", "next_actions"),
            ),
            ReasoningMode(
                "explanation",
                "Explain a concept or boundary clearly.",
                ("explanation", "implications"),
            ),
            ReasoningMode(
                "question_answering",
                "Answer using only available evidence.",
                ("answer", "evidence", "limitations"),
            ),
        )
    )


def build_default_reasoning_engine() -> ExecutiveReasoningEngine:
    return ExecutiveReasoningEngine()


def is_executive_reasoning_engine_enabled() -> bool:
    value = os.getenv("HERMES_EXECUTIVE_REASONING_ENGINE_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_reasoning_planner_enabled() -> bool:
    value = os.getenv("HERMES_REASONING_PLANNER_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_skill_selection_enabled() -> bool:
    value = os.getenv("HERMES_SKILL_SELECTION_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_ai_provider_selection_enabled() -> bool:
    value = os.getenv("HERMES_AI_PROVIDER_SELECTION_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_planning_engine_enabled() -> bool:
    try:
        from gateway.executive_planning import is_planning_engine_enabled as _enabled

        return _enabled()
    except Exception:
        value = os.getenv("HERMES_PLANNING_ENGINE_ENABLED")
        return True if value is None else is_truthy_value(value)


def build_reasoning_status() -> dict[str, Any]:
    registry = build_default_reasoning_mode_registry()
    return {
        "enabled": is_executive_reasoning_engine_enabled(),
        "reasoning_planner_enabled": is_reasoning_planner_enabled(),
        "skill_selection_enabled": is_skill_selection_enabled(),
        "ai_provider_selection_enabled": is_ai_provider_selection_enabled(),
        "planning_engine_enabled": is_planning_engine_enabled(),
        "execution_boundary": "not_executed",
        "live_execution_enabled": False,
        "external_calls_enabled": False,
        "skill_execution": "selected_not_executed",
        "available_modes": list(registry.mode_ids()),
        "redacted": True,
    }


def render_reasoning_result_for_prompt(result: ExecutiveReasoningResult) -> str:
    plan = result.reasoning_plan
    response = result.response_plan
    lines = [
        "EXECUTIVE REASONING PLAN",
        f"Reasoning mode: {plan.reasoning_mode}",
        f"User objective: {plan.user_objective}",
        "Evidence plan:",
    ]
    for need in plan.evidence_needs:
        state = "available" if need.available else "missing"
        refs = ", ".join(need.evidence_refs) if need.evidence_refs else "none"
        lines.append(
            f"- {need.evidence_type} from {need.source_category}: {state}; refs={refs}"
        )
        if need.limitation:
            lines.append(f"  limitation: {need.limitation}")
    lines.extend([
        "Confidence:",
        *[
            f"- {claim}: {level.value}"
            for claim, level in sorted(plan.confidence_by_claim.items())
        ],
        "Selected skills:",
        f"- {', '.join(plan.selected_skills) if plan.selected_skills else 'none'}",
        f"Skill execution: {plan.skill_execution}",
        f"Selected model: {response.selected_model}",
        f"Response structure: {', '.join(response.expected_structure)}",
        "Constraints:",
    ])
    lines.extend(f"- {constraint}" for constraint in plan.constraints)
    lines.append("Execution required: false")
    lines.append("Execution permitted: false")
    return "\n".join(lines)


def _select_reasoning_mode(request: ReasoningPlanningRequest) -> str:
    text = request.normalized_user_request.casefold()
    classification = request.request_classification
    if classification == "planning_request":
        return "planning_stub"
    if classification == "daily_brief":
        return "executive_brief"
    if classification == "decision_support":
        return "comparison" if _contains_choice(text) else "analysis"
    if classification == "approval_related":
        return "review"
    if classification == "deterministic_ovos_command":
        return "direct_answer"
    if classification == "unsupported_or_unsafe":
        return "direct_answer"
    if classification == "executive_status":
        if _contains_any(text, ("summarise", "summary", "top three", "priorit")):
            return "executive_summary"
        return "question_answering"
    return "direct_answer"


def _plan_evidence(request: ReasoningPlanningRequest) -> tuple[EvidenceNeed, ...]:
    text = request.normalized_user_request.casefold()
    refs = tuple(_safe_label(ref) for ref in request.evidence_refs)
    needs: list[EvidenceNeed] = []
    if _contains_any(text, ("meeting", "calendar", "schedule")):
        meeting_refs = _refs_available_for(request, ("meeting", "calendar_context"))
        needs.append(
            EvidenceNeed(
                evidence_type="schedule_context",
                source_category="calendar_context",
                required=True,
                available=bool(meeting_refs),
                evidence_refs=meeting_refs,
                limitation=None
                if meeting_refs
                else "Calendar or meeting evidence is unavailable.",
            )
        )
    if "gmail" in text or "email" in text:
        needs.append(
            EvidenceNeed(
                evidence_type="email_context",
                source_category="gmail_context",
                required=False,
                available=False,
                evidence_refs=(),
                limitation="Gmail context is unavailable in this milestone.",
            )
        )
    if "clickup" in text or "task" in text:
        needs.append(
            EvidenceNeed(
                evidence_type="task_context",
                source_category="clickup_context",
                required=False,
                available=False,
                evidence_refs=(),
                limitation="ClickUp context is unavailable in this milestone.",
            )
        )
    if "news" in text or "portfolio" in text or "investment" in text:
        needs.append(
            EvidenceNeed(
                evidence_type="live_external_context",
                source_category="external_market_or_news_context",
                required=False,
                available=False,
                evidence_refs=(),
                limitation="Live news and investment portfolio context are unavailable.",
            )
        )
    if request.request_classification in {"executive_status", "daily_brief"}:
        available = bool(refs)
        needs.append(
            EvidenceNeed(
                evidence_type="executive_context",
                source_category="hermes_context",
                required=False,
                available=available,
                evidence_refs=refs,
                limitation=None
                if available
                else "No matching Hermes context evidence was selected.",
            )
        )
    if not needs:
        needs.append(
            EvidenceNeed(
                evidence_type="current_request",
                source_category="current_request_metadata",
                required=True,
                available=True,
                evidence_refs=refs,
            )
        )
    return tuple(needs)


def _confidence_by_claim(
    request: ReasoningPlanningRequest,
    evidence_needs: tuple[EvidenceNeed, ...],
) -> dict[str, ConfidenceLevel]:
    confidence: dict[str, ConfidenceLevel] = {
        "current_request": ConfidenceLevel.KNOWN,
    }
    for need in evidence_needs:
        claim = need.evidence_type
        confidence[claim] = (
            ConfidenceLevel.KNOWN if need.available else ConfidenceLevel.UNAVAILABLE
        )
    if request.request_classification == "decision_support":
        confidence["recommendation"] = ConfidenceLevel.DERIVED
    if request.request_classification == "planning_request":
        confidence["plan_outline"] = ConfidenceLevel.DERIVED
    return confidence


def _constraints_for_request(
    request: ReasoningPlanningRequest,
    evidence_needs: tuple[EvidenceNeed, ...],
) -> tuple[str, ...]:
    constraints = [
        "Use only labelled evidence selected by Hermes.",
        "Do not invent evidence or promote assumptions to facts.",
        "Skills may be selected but must not be executed.",
        "External execution remains unavailable and not_executed.",
    ]
    if any(
        need.evidence_type == "schedule_context" and not need.available
        for need in evidence_needs
    ):
        constraints.append("Do not infer meetings without meeting evidence.")
    if request.request_classification == "potentially_executable":
        constraints.append("Return a non-executing limitation or proposal only.")
    return tuple(constraints)


def _select_skills(request: ReasoningPlanningRequest) -> tuple[str, ...]:
    if not is_skill_selection_enabled():
        return ()
    text = request.normalized_user_request.casefold()
    if request.request_classification == "planning_request":
        return ("milestone_planning",)
    if request.request_classification == "decision_support":
        return ("executive_decision_support",)
    if "lease" in text or "contract" in text:
        return ("document_review",)
    if "white paper" in text or "policy" in text:
        return ("policy_review",)
    return ()


def _select_provider(mode: str, request: ReasoningPlanningRequest) -> str:
    if not is_ai_provider_selection_enabled():
        return "standard_conversational_model"
    if request.request_classification == "deterministic_ovos_command":
        return "deterministic_response"
    if mode in {"analysis", "comparison", "planning_stub", "review"}:
        return "reasoning_model"
    return "standard_conversational_model"


def _objective_for_request(request: ReasoningPlanningRequest) -> str:
    text = request.normalized_user_request
    if request.request_classification == "planning_request":
        return "Create a non-executing milestone planning outline."
    if request.request_classification == "decision_support":
        return "Compare the available options and recommend a practical path."
    if request.request_classification == "daily_brief":
        return "Answer the daily brief request from available Hermes context."
    if _contains_any(text.casefold(), ("meeting", "calendar", "schedule")):
        return "Answer schedule availability only from selected evidence."
    return "Answer the current request clearly using selected context and limits."


def _sub_questions_for_request(request: ReasoningPlanningRequest) -> tuple[str, ...]:
    text = request.normalized_user_request.casefold()
    if request.request_classification == "decision_support":
        return (
            "What options is the user comparing?",
            "What evidence is available for each option?",
            "What recommendation follows from known constraints?",
        )
    if request.request_classification == "planning_request":
        return (
            "What milestone outcome is being planned?",
            "What can be planned without execution?",
            "What boundaries must remain active?",
        )
    if _contains_any(text, ("meeting", "calendar", "schedule")):
        return (
            "What schedule evidence is available?",
            "What schedule evidence is missing?",
        )
    return ("What answer is supported by selected evidence?",)


def _clarification_needed(
    request: ReasoningPlanningRequest,
    evidence_needs: tuple[EvidenceNeed, ...],
) -> bool:
    del request
    return any(need.required and not need.available for need in evidence_needs)


def _expected_structure_for_mode(mode: str) -> tuple[str, ...]:
    return build_default_reasoning_mode_registry().lookup(mode).expected_structure


def _refs_available_for(
    request: ReasoningPlanningRequest,
    categories: tuple[str, ...],
) -> tuple[str, ...]:
    for category in categories:
        if int(request.context_source_counts.get(category, 0) or 0) > 0:
            return tuple(_safe_label(ref) for ref in request.evidence_refs)
    return ()


def _stable_seed(request: ReasoningPlanningRequest, mode: str) -> str:
    return json.dumps(
        {
            "correlation_id": request.correlation_id,
            "classification": request.request_classification,
            "context_counts": dict(sorted(request.context_source_counts.items())),
            "evidence_refs": list(request.evidence_refs),
            "mode": mode,
            "safety_state": request.safety_state,
            "text_digest": _digest(request.normalized_user_request)[:16],
        },
        sort_keys=True,
    )


def _contains_choice(text: str) -> bool:
    return bool(re.search(r"\b(or|versus|vs\.?|first)\b", text))


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _safe_label(value: str | None) -> str:
    text = " ".join(str(value or "").split())
    return re.sub(
        r"(?i)(api[_-]?key|token|secret|password)=\S+", r"\1=[REDACTED]", text
    )[:180]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
