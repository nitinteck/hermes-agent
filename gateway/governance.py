"""Governance hardening for user-channel Hermes responses."""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from utils import is_truthy_value


PUBLIC_SAFE = "public_safe"
USER_SAFE = "user_safe"
INTERNAL = "internal"
RESTRICTED_OPERATOR = "restricted_operator"


@dataclass(frozen=True)
class DisclosureClassification:
    disclosure_class: str
    reason_code: str


@dataclass(frozen=True)
class RestrictedConcept:
    concept_id: str
    patterns: tuple[str, ...]
    disclosure_class: str = INTERNAL
    safe_replacement: str = ""


@dataclass(frozen=True)
class DisclosureDecision:
    allowed: bool
    disclosure_class: str
    matched_concepts: tuple[str, ...] = ()
    action: str = "allow"


@dataclass(frozen=True)
class ImprovementProposal:
    proposal_id: str
    trigger_request_id: str
    proposal_type: str
    target_scope: str
    rationale: str
    evidence_summary: str
    proposed_diff_summary: str
    risk_class: str
    rollback_plan: str
    review_status: str = "proposed"
    approval_status: str = "not_requested"
    application_status: str = "not_applied"
    created_at: int = 0
    trace_metadata: Mapping[str, Any] = field(default_factory=dict)

    def safe_trace(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "trigger_request_id": self.trigger_request_id,
            "proposal_type": self.proposal_type,
            "target_scope": self.target_scope,
            "rationale_digest": _digest(self.rationale)[:16],
            "evidence_digest": _digest(self.evidence_summary)[:16],
            "proposed_diff_digest": _digest(self.proposed_diff_summary)[:16],
            "risk_class": self.risk_class,
            "review_status": self.review_status,
            "approval_status": self.approval_status,
            "application_status": self.application_status,
            "created_at": self.created_at,
            "trace_metadata": dict(self.trace_metadata),
        }


@dataclass(frozen=True)
class ResponseSanitizationResult:
    final_response: str
    disclosure_decision: DisclosureDecision
    warnings: tuple[str, ...] = ()
    improvement_proposal: ImprovementProposal | None = None
    capability_truth: Mapping[str, Any] = field(default_factory=dict)


class IPDisclosurePolicy:
    def __init__(self, concepts: tuple[RestrictedConcept, ...] | None = None) -> None:
        self.concepts = concepts or _default_restricted_concepts()

    def classify(self, text: str, *, channel: str = "whatsapp") -> DisclosureDecision:
        if channel not in {"whatsapp", "whatsapp_cloud"}:
            return DisclosureDecision(True, USER_SAFE)
        if "external execution is unavailable" in text.casefold():
            return DisclosureDecision(True, USER_SAFE)
        matched: list[str] = []
        for concept in self.concepts:
            if any(
                re.search(pattern, text, flags=re.IGNORECASE)
                for pattern in concept.patterns
            ):
                matched.append(concept.concept_id)
        if matched:
            return DisclosureDecision(
                False,
                USER_SAFE,
                tuple(sorted(set(matched))),
                action="sanitize",
            )
        return DisclosureDecision(True, USER_SAFE)


def is_ip_confidentiality_guard_enabled() -> bool:
    value = os.getenv("HERMES_IP_CONFIDENTIALITY_GUARD_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_response_output_inspection_enabled() -> bool:
    value = os.getenv("HERMES_RESPONSE_OUTPUT_INSPECTION_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_self_improvement_direct_mutation_enabled() -> bool:
    return is_truthy_value(os.getenv("HERMES_SELF_IMPROVEMENT_DIRECT_MUTATION_ENABLED"))


def is_improvement_proposal_generation_enabled() -> bool:
    value = os.getenv("HERMES_IMPROVEMENT_PROPOSAL_GENERATION_ENABLED")
    return True if value is None else is_truthy_value(value)


def is_improvement_proposal_application_enabled() -> bool:
    return is_truthy_value(os.getenv("HERMES_IMPROVEMENT_PROPOSAL_APPLICATION_ENABLED"))


def build_governance_status() -> dict[str, Any]:
    return {
        "ip_confidentiality_guard_enabled": is_ip_confidentiality_guard_enabled(),
        "response_output_inspection_enabled": is_response_output_inspection_enabled(),
        "self_improvement_direct_mutation_enabled": is_self_improvement_direct_mutation_enabled(),
        "improvement_proposal_generation_enabled": is_improvement_proposal_generation_enabled(),
        "improvement_proposal_application_enabled": is_improvement_proposal_application_enabled(),
        "default_whatsapp_disclosure_class": USER_SAFE,
        "operator_mode_enabled": False,
        "redacted": True,
    }


def sanitize_user_channel_response(
    response: str,
    *,
    request: str,
    channel: str,
    correlation_id: str,
) -> ResponseSanitizationResult:
    warnings: list[str] = []
    final_response = _redact_secrets(response)
    proposal = None
    if _looks_like_self_improvement(final_response):
        if is_improvement_proposal_generation_enabled():
            proposal = _proposal_from_response(
                final_response,
                request=request,
                correlation_id=correlation_id,
            )
        final_response = (
            "I have noted a possible improvement for review. I have not changed "
            "skills, memory, profile, prompts, routing or behaviour."
        )
        warnings.append("self_improvement_quarantined")

    decision = IPDisclosurePolicy().classify(final_response, channel=channel)
    if not decision.allowed and is_ip_confidentiality_guard_enabled():
        final_response = (
            "Hermes gathers relevant information, analyses priorities, supports "
            "decisions, and prepares proposed plans. I can explain capabilities "
            "plainly, but I cannot share internal implementation details here."
        )
        warnings.append("ip_disclosure_sanitized")
    return ResponseSanitizationResult(
        final_response=final_response,
        disclosure_decision=decision,
        warnings=tuple(warnings),
        improvement_proposal=proposal,
    )


def _looks_like_self_improvement(text: str) -> bool:
    folded = text.casefold()
    return any(
        marker in folded
        for marker in (
            "self-improvement review",
            "user profile updated",
            "skill created",
            "skill updated",
            "full rewrite",
            "prompt updated",
            "routing updated",
            "policy updated",
        )
    )


def _proposal_from_response(
    response: str,
    *,
    request: str,
    correlation_id: str,
) -> ImprovementProposal:
    seed = f"{correlation_id}|{_digest(response)}"
    return ImprovementProposal(
        proposal_id=f"iprop_{_digest(seed)[:16]}",
        trigger_request_id=correlation_id,
        proposal_type="self_improvement_quarantine",
        target_scope="skills_profile_prompts_routing_policy",
        rationale="A normal user-channel response attempted to expose or apply a self-improvement mutation.",
        evidence_summary=f"response_digest={_digest(response)[:16]} request_digest={_digest(request)[:16]}",
        proposed_diff_summary="No change applied; proposal retained for owner review only.",
        risk_class="medium",
        rollback_plan="No rollback required because no mutation was applied.",
        created_at=int(time.time()),
        trace_metadata={"source": "response_sanitizer"},
    )


def _default_restricted_concepts() -> tuple[RestrictedConcept, ...]:
    return (
        RestrictedConcept("repo_names", (r"\bnitinteck/(hermes-agent|ovos-core)\b",)),
        RestrictedConcept(
            "file_paths",
            (
                r"(/opt/ai-stack|/Users/|gateway/[A-Za-z0-9_./-]+\.py|hermes_cli/[A-Za-z0-9_./-]+\.py)",
            ),
        ),
        RestrictedConcept(
            "class_names",
            (
                r"\b(GatewayRunner|ExecutiveOrchestrator|ExecutivePlanningEngine|AIAgent)\b",
            ),
        ),
        RestrictedConcept(
            "method_names",
            (r"\b(_handle_message|prepare_turn|observe_response|run_conversation)\b",),
        ),
        RestrictedConcept("trace_ids", (r"\b(trace|eo)_[a-f0-9]{6,}\b",)),
        RestrictedConcept("commit_hashes", (r"\b[0-9a-f]{12,40}\b",)),
        RestrictedConcept("feature_flags", (r"\bHERMES_[A-Z0-9_]+\b",)),
        RestrictedConcept("service_names", (r"\bhermes-gateway\.service\b",)),
        RestrictedConcept(
            "internal_terms",
            (
                r"\b(controlled execution boundary|execution_boundary|Safety Kernel|adapter unavailable|capability registry)\b",
            ),
        ),
        RestrictedConcept(
            "prompts", (r"\bsystem prompt\b|\btrusted orchestration instructions\b",)
        ),
    )


def _redact_secrets(text: str) -> str:
    redacted = re.sub(
        r"(?i)(api[_-]?key|token|secret|password)=\S+", r"\1=[REDACTED]", text
    )
    redacted = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED]", redacted)
    return redacted


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
