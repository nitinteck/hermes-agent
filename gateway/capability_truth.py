"""Deterministic user-safe capability truth for Hermes governance."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any

from utils import is_truthy_value


@dataclass(frozen=True)
class CapabilityTruth:
    capability_id: str
    capability_group: str
    availability: bool
    read_available: bool = False
    write_available: bool = False
    approval_available: bool = False
    execution_available: bool = False
    authorisation_state: str = "not_authorised"
    connection_state: str = "not_connected"
    reason_code: str = "unavailable"
    safe_user_message: str = ""
    safe_operator_message: str = ""
    source_of_truth: str = "deterministic_registry"
    effective_at: int = 0
    expires_at: int | None = None
    tenant_scope: str = "all"
    user_scope: str = "all"
    sensitivity: str = "user_safe"

    def safe_trace(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "capability_group": self.capability_group,
            "availability": self.availability,
            "read_available": self.read_available,
            "write_available": self.write_available,
            "approval_available": self.approval_available,
            "execution_available": self.execution_available,
            "authorisation_state": self.authorisation_state,
            "connection_state": self.connection_state,
            "reason_code": self.reason_code,
            "source_of_truth": self.source_of_truth,
            "tenant_scope": self.tenant_scope,
            "user_scope": self.user_scope,
            "sensitivity": self.sensitivity,
            "digest": hashlib.sha256(
                f"{self.capability_id}|{self.reason_code}|{self.availability}".encode()
            ).hexdigest()[:16],
        }


class CapabilityTruthRegistry:
    def __init__(self, records: tuple[CapabilityTruth, ...]) -> None:
        self._records = {record.capability_id: record for record in records}

    def get(self, capability_id: str) -> CapabilityTruth:
        return self._records[capability_id]

    def list_all(self) -> tuple[CapabilityTruth, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def status(self) -> dict[str, Any]:
        records = self.list_all()
        return {
            "enabled": is_capability_truth_enabled(),
            "capability_count": len(records),
            "available_count": sum(1 for record in records if record.availability),
            "external_execution_available": False,
            "external_mutations_enabled": False,
            "live_execution_enabled": False,
            "redacted": True,
            "safe_digest": hashlib.sha256(
                "|".join(record.capability_id for record in records).encode()
            ).hexdigest()[:16],
        }


def is_capability_truth_enabled() -> bool:
    value = os.getenv("HERMES_CAPABILITY_TRUTH_REGISTRY_ENABLED")
    return True if value is None else is_truthy_value(value)


def build_default_capability_truth_registry() -> CapabilityTruthRegistry:
    now = int(time.time())
    return CapabilityTruthRegistry((
        CapabilityTruth(
            "planning",
            "planning",
            True,
            safe_user_message="I can help prepare proposed plans.",
            safe_operator_message="Planning Engine available; execution false.",
            reason_code="available_proposal_only",
            effective_at=now,
        ),
        CapabilityTruth(
            "planning_execution",
            "planning",
            False,
            safe_user_message="Plans are proposals only; I cannot execute them.",
            reason_code="execution_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "google_calendar",
            "calendar",
            False,
            read_available=False,
            write_available=False,
            authorisation_state="not_authorised",
            connection_state="not_connected",
            safe_user_message="No Google Calendar account is currently authorised.",
            safe_operator_message="Calendar authorisation false; reads false; writes false.",
            reason_code="calendar_not_authorised",
            effective_at=now,
        ),
        CapabilityTruth(
            "email",
            "email",
            False,
            read_available=False,
            write_available=False,
            safe_user_message="Email access and sending are not currently enabled.",
            reason_code="email_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "task_management",
            "tasks",
            False,
            read_available=False,
            write_available=False,
            safe_user_message="Task-system access is not currently enabled.",
            reason_code="tasks_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "reminders",
            "reminders",
            False,
            safe_user_message="Reminder scheduling is not currently enabled.",
            reason_code="reminders_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "external_execution",
            "execution",
            False,
            execution_available=False,
            safe_user_message="I cannot take external actions yet.",
            reason_code="execution_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "approval_recording",
            "approval",
            False,
            approval_available=False,
            safe_user_message="Approval recording is not currently enabled.",
            reason_code="approval_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "mcp_execution",
            "mcp",
            False,
            safe_user_message="MCP execution is not enabled.",
            reason_code="mcp_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "shell_execution",
            "execution",
            False,
            safe_user_message="Shell execution is not enabled.",
            reason_code="shell_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "webhook_execution",
            "execution",
            False,
            safe_user_message="Webhook execution is not enabled.",
            reason_code="webhooks_disabled",
            effective_at=now,
        ),
        CapabilityTruth(
            "self_modification_application",
            "self_improvement",
            False,
            safe_user_message="Self-improvement changes require review and are not applied automatically.",
            reason_code="application_disabled",
            effective_at=now,
        ),
    ))


def user_safe_capability_answer(message: str) -> str | None:
    text = message.casefold()
    registry = build_default_capability_truth_registry()
    if "which google calendar account" in text or "calendar account" in text:
        return registry.get("google_calendar").safe_user_message
    if "can you read" in text and any(
        connector in text for connector in ("gmail", "calendar", "clickup")
    ):
        return (
            "I cannot access Gmail, live Calendar or ClickUp today. "
            "No Google Calendar account is currently authorised, Gmail is not "
            "connected, ClickUp is not connected, and I cannot send, create, "
            "modify or delete external records; execution remains not_executed."
        )
    if "meetings" in text or "calendar" in text:
        if "read" in text or "have" in text or "tomorrow" in text or "today" in text:
            return "I cannot access your live Calendar yet."
    if "email" in text and ("how many" in text or "sent" in text):
        return "Hermes has no enabled email-sending capability, so it should have sent none."
    if "remind" in text or "reminder" in text:
        return registry.get("reminders").safe_user_message
    return None
