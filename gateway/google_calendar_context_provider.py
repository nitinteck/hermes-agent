"""Read-only Google Calendar executive context provider.

This module is a controlled external read boundary. It never creates, updates,
deletes, sends, schedules, or dispatches anything; raw Google Calendar payloads
are normalised into Hermes-owned context contributions before the LLM sees them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time as dt_time, timedelta, timezone
import hashlib
import json
import os
import re
from typing import Any, Mapping
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from gateway.executive_context_providers import (
    ContextEvidenceReference,
    ExecutiveContextContribution,
    ExecutiveContextProviderMetadata,
    ExecutiveContextProviderRequest,
)
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
    IntegrationRequest,
    IntegrationService,
    IntegrationState,
    InMemoryCapabilityRegistry,
    ResolvedCredential,
)
from utils import is_truthy_value


GOOGLE_CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
EXECUTION_BOUNDARY = "not_executed"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalise_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _safe_label(value: str | None, *, limit: int = 160) -> str:
    text = _normalise_text(value or "unknown")
    text = re.sub(
        r"(?i)(api[_-]?key|token|secret|password)\s*=\s*\S+", "[REDACTED]", text
    )
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._-]+", "[REDACTED]", text)
    return text[:limit]


def _env_truthy(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else is_truthy_value(value)


@dataclass(frozen=True)
class GoogleCalendarWindow:
    start: datetime
    end: datetime
    label: str

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("calendar query window must be timezone-aware")
        if self.end <= self.start:
            raise ValueError("calendar query window end must be after start")


@dataclass(frozen=True)
class GoogleCalendarProviderConfig:
    provider_enabled: bool = True
    live_reads_enabled: bool = False
    descriptions_enabled: bool = False
    write_capability_enabled: bool = False
    token_file: str | None = None
    client_secret_file: str | None = None
    connection_id: str = "google-calendar-primary"
    tenant_id: str = "default"
    user_id: str | None = None
    environment: str = "production"
    calendar_id: str = "primary"
    default_timezone: str = "Europe/London"
    max_events: int = 25
    max_range_days: int = 7
    timeout_seconds: float = 5.0
    max_pages: int = 3
    workday_start: str = "09:00"
    workday_end: str = "17:30"
    credential_status_override: str | None = None
    now: Callable[[], datetime] = field(default=_now_utc, compare=False)

    @classmethod
    def from_environment(cls) -> GoogleCalendarProviderConfig:
        return cls(
            provider_enabled=_env_truthy(
                "HERMES_GOOGLE_CALENDAR_CONTEXT_PROVIDER_ENABLED", default=True
            ),
            live_reads_enabled=_env_truthy(
                "HERMES_GOOGLE_CALENDAR_LIVE_READS_ENABLED", default=False
            ),
            descriptions_enabled=_env_truthy(
                "HERMES_GOOGLE_CALENDAR_DESCRIPTIONS_ENABLED", default=False
            ),
            write_capability_enabled=False,
            token_file=os.getenv("HERMES_GOOGLE_CALENDAR_TOKEN_FILE") or None,
            client_secret_file=os.getenv("HERMES_GOOGLE_CALENDAR_CLIENT_SECRET_FILE")
            or None,
            connection_id=os.getenv("HERMES_GOOGLE_CALENDAR_CONNECTION_ID")
            or "google-calendar-primary",
            tenant_id=os.getenv("HERMES_TENANT_ID") or "default",
            user_id=os.getenv("HERMES_GOOGLE_CALENDAR_USER_ID")
            or os.getenv("HERMES_USER_ID")
            or None,
            environment=os.getenv("HERMES_ENVIRONMENT") or "production",
            calendar_id=os.getenv("HERMES_GOOGLE_CALENDAR_ID") or "primary",
            default_timezone=os.getenv("HERMES_GOOGLE_CALENDAR_TIMEZONE")
            or "Europe/London",
            max_events=_bounded_int(
                os.getenv("HERMES_GOOGLE_CALENDAR_MAX_EVENTS"),
                default=25,
                low=1,
                high=50,
            ),
            max_range_days=_bounded_int(
                os.getenv("HERMES_GOOGLE_CALENDAR_MAX_RANGE_DAYS"),
                default=7,
                low=1,
                high=14,
            ),
            timeout_seconds=float(
                os.getenv("HERMES_GOOGLE_CALENDAR_TIMEOUT_SECONDS") or 5.0
            ),
            max_pages=_bounded_int(
                os.getenv("HERMES_GOOGLE_CALENDAR_MAX_PAGES"), default=3, low=1, high=5
            ),
            workday_start=os.getenv("HERMES_GOOGLE_CALENDAR_WORKDAY_START") or "09:00",
            workday_end=os.getenv("HERMES_GOOGLE_CALENDAR_WORKDAY_END") or "17:30",
        )


def _bounded_int(value: str | None, *, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return min(high, max(low, parsed))


class GoogleCalendarReadAdapter:
    """Read-only Google Calendar adapter used behind IntegrationService."""

    metadata = IntegrationAdapterMetadata(
        adapter_id="calendar_google_rest",
        integration_id="google_calendar",
        version="1.0.0",
        authentication_types=("oauth_bearer",),
        supported_capability_ids=("calendar.events.read",),
        uses_external_data=True,
        deterministic=True,
        timeout_seconds=5.0,
        retry_max_attempts=1,
        sensitivity="private",
    )

    def __init__(self, *, config: GoogleCalendarProviderConfig) -> None:
        self.config = config

    def execute_read(
        self,
        request: IntegrationRequest,
        connection: ConnectionDefinition,
        credential: ResolvedCredential,
    ) -> Mapping[str, Any]:
        calendar = self._get_primary_calendar(credential.value)
        tz_name = str(calendar.get("timeZone") or self.config.default_timezone)
        window = _window_from_parameters(request.parameters, default_timezone=tz_name)
        events = self._list_events(
            token=credential.value,
            calendar_id=str(calendar.get("id") or self.config.calendar_id),
            window=window,
            max_results=int(
                request.parameters.get("max_results") or self.config.max_events
            ),
        )
        return {"calendar": calendar, "items": events.get("items", [])}

    def _get_primary_calendar(self, token: str) -> Mapping[str, Any]:
        url = (
            "https://www.googleapis.com/calendar/v3/calendars/"
            f"{quote(self.config.calendar_id, safe='')}"
        )
        return self._get_json(url, token)

    def _list_events(
        self,
        *,
        token: str,
        calendar_id: str,
        window: GoogleCalendarWindow,
        max_results: int,
    ) -> Mapping[str, Any]:
        params = {
            "timeMin": window.start.isoformat(),
            "timeMax": window.end.isoformat(),
            "singleEvents": "true",
            "showDeleted": "false",
            "orderBy": "startTime",
            "maxResults": str(max_results),
        }
        url = (
            "https://www.googleapis.com/calendar/v3/calendars/"
            f"{quote(calendar_id, safe='')}/events?{urlencode(params)}"
        )
        pages: list[Mapping[str, Any]] = []
        next_url: str | None = url
        for _ in range(max(1, self.config.max_pages)):
            if not next_url:
                break
            payload = self._get_json(next_url, token)
            pages.append(payload)
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
            params["pageToken"] = str(page_token)
            next_url = (
                "https://www.googleapis.com/calendar/v3/calendars/"
                f"{quote(calendar_id, safe='')}/events?{urlencode(params)}"
            )
        items: list[Mapping[str, Any]] = []
        for page in pages:
            page_items = page.get("items")
            if isinstance(page_items, list):
                items.extend(item for item in page_items if isinstance(item, Mapping))
        return {"items": items[:max_results]}

    def _get_json(self, url: str, token: str) -> Mapping[str, Any]:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, Mapping) else {}


def _window_from_parameters(
    parameters: Mapping[str, Any], *, default_timezone: str
) -> GoogleCalendarWindow:
    tz = _timezone(str(parameters.get("timezone") or default_timezone))
    start_raw = str(parameters.get("window_start") or "")
    end_raw = str(parameters.get("window_end") or "")
    label = str(parameters.get("window_label") or "requested")
    start = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone(tz)
    end = datetime.fromisoformat(end_raw.replace("Z", "+00:00")).astimezone(tz)
    return GoogleCalendarWindow(start=start, end=end, label=label)


def build_google_calendar_integration_service(
    config: GoogleCalendarProviderConfig,
) -> IntegrationService:
    connections = ConnectionRegistry()
    connections.register_integration(
        IntegrationDefinition(
            integration_id="google_calendar",
            display_name="Google Calendar",
            integration_type="native_api",
            version="1.0.0",
            environment=config.environment,
        )
    )
    credential_ref = (
        CredentialReference(
            credential_ref_id=f"{config.connection_id}:credential",
            integration_id="google_calendar",
            tenant_id=config.tenant_id,
            user_id=config.user_id,
            environment=config.environment,
            source="json_file_field",
            key=config.token_file,
            safe_metadata={"field": "access_token"},
        )
        if config.token_file
        else None
    )
    connection_state = (
        IntegrationState.CONNECTED
        if config.live_reads_enabled
        and config.token_file
        and os.path.exists(config.token_file)
        else IntegrationState.AUTHORISATION_REQUIRED
    )
    connections.register_connection(
        ConnectionDefinition(
            connection_id=config.connection_id,
            integration_id="google_calendar",
            owner_tenant_id=config.tenant_id,
            owner_user_id=config.user_id,
            connection_name="Google Calendar primary",
            authentication_method="oauth_bearer",
            scopes=(GOOGLE_CALENDAR_READONLY_SCOPE,),
            status=connection_state,
            enabled=config.provider_enabled,
            created_at=_now_utc().isoformat(),
            credential_ref=credential_ref,
            capability_ids=("calendar.events.read",),
            environment=config.environment,
        )
    )
    capabilities = InMemoryCapabilityRegistry()
    capabilities.register(
        IntegrationCapability(
            capability_id="calendar.events.read",
            integration_id="google_calendar",
            adapter_id=GoogleCalendarReadAdapter.metadata.adapter_id,
            operation_name="events.list",
            category="context_read",
            read_write="read",
            risk_class="low",
            required_scopes=(GOOGLE_CALENDAR_READONLY_SCOPE,),
            required_permissions=(),
            required_approval_class="none",
            input_schema_ref="google_calendar.events.read.v1",
            output_schema_ref="google_calendar.events.v1",
            tenant_scope="tenant",
            user_scope="user",
            enabled=config.provider_enabled and not config.write_capability_enabled,
            environment=config.environment,
            health_dependency="google_calendar",
            lifecycle_state="active",
        )
    )
    adapters = IntegrationAdapterRegistry()
    adapters.register(GoogleCalendarReadAdapter(config=config))
    return IntegrationService(
        connection_registry=connections,
        capability_registry=capabilities,
        adapter_registry=adapters,
        credential_resolver=EnvironmentCredentialResolver(),
    )


def google_calendar_capability_status(
    config: GoogleCalendarProviderConfig | None = None,
) -> str:
    cfg = config or GoogleCalendarProviderConfig.from_environment()
    if not cfg.provider_enabled:
        return "disabled"
    if not cfg.live_reads_enabled:
        return "configured_awaiting_live_read_enablement"
    if cfg.credential_status_override:
        return cfg.credential_status_override
    if not cfg.token_file or not os.path.exists(cfg.token_file):
        return "awaiting_user_calendar_authorisation"
    return "connected"


def should_select_google_calendar_context(
    message: str, request_classification: str
) -> bool:
    if request_classification in {"potentially_executable", "unsupported_or_unsafe"}:
        return False
    text = _normalise_text(message).casefold()
    if not text:
        return False
    if re.search(
        r"\b(build|add|implement|connector|provider|integration|architecture|mvp|milestone)\b",
        text,
    ):
        if re.search(
            r"\b(gmail|clickup|connector|provider|integration|architecture)\b", text
        ):
            return False
    if request_classification == "daily_brief":
        return True
    return bool(
        re.search(
            r"\b(calendar|diary|meeting|meetings|agenda|schedule|scheduled|availability|available|free time|free block|conflict|conflicts|next event|next meeting|prep|prepare)\b",
            text,
        )
    )


class GoogleCalendarContextProvider:
    provider_id = "google_calendar_context"

    def __init__(
        self,
        *,
        config: GoogleCalendarProviderConfig | None = None,
        integration_service: IntegrationService | None = None,
        connection_id: str | None = None,
    ) -> None:
        self.config = config or GoogleCalendarProviderConfig.from_environment()
        self.integration_service = integration_service
        self.connection_id = connection_id or self.config.connection_id
        self.metadata = ExecutiveContextProviderMetadata(
            provider_id=self.provider_id,
            version="1.0.0",
            provider_type="external_read_only",
            supported_context_types=(
                "meeting",
                "availability",
                "schedule_summary",
                "calendar_conflict",
                "preparation_requirement",
                "calendar_capability_status",
            ),
            source_mechanism="google_calendar_api_read_only",
            enabled=self.config.provider_enabled,
            deterministic=True,
            uses_external_data=True,
            timeout_ms=int(max(1.0, self.config.timeout_seconds) * 1000),
            sensitivity="private",
            health_state=google_calendar_capability_status(self.config),
        )

    def collect(
        self,
        request: ExecutiveContextProviderRequest,
    ) -> tuple[ExecutiveContextContribution, ...]:
        status = google_calendar_capability_status(self.config)
        service = self.integration_service or build_google_calendar_integration_service(
            self.config
        )
        if status != "connected" and self.integration_service is None:
            return (self._capability_status(request, status),)
        if self.config.write_capability_enabled:
            return (self._capability_status(request, "write_capability_forbidden"),)

        calendar_tz = _timezone(self.config.default_timezone)
        window = self._window_for_request(request, calendar_tz)
        result = service.execute_read(
            IntegrationRequest(
                capability_id="calendar.events.read",
                connection_id=self.connection_id,
                actor_scope=ActorScope(
                    tenant_id=request.turn.tenant_id,
                    user_id=request.turn.actor_id,
                    environment=self.config.environment,
                ),
                parameters={
                    "calendar_id": self.config.calendar_id,
                    "window_start": window.start.isoformat(),
                    "window_end": window.end.isoformat(),
                    "window_label": window.label,
                    "timezone": self.config.default_timezone,
                    "max_results": self.config.max_events,
                    "max_pages": self.config.max_pages,
                },
                trace_context={
                    "provider_id": self.provider_id,
                    "conversation_id": request.turn.conversation_id,
                    "classification": request.request_classification,
                },
            )
        )
        if result.status != "ok":
            error_status = (
                result.error.code if result.error else "integration_unavailable"
            )
            return (self._capability_status(request, error_status),)
        payload = result.data
        calendar_meta_value = (
            payload.get("calendar") if isinstance(payload, Mapping) else {}
        )
        calendar_meta = (
            calendar_meta_value if isinstance(calendar_meta_value, Mapping) else {}
        )
        calendar_tz = _timezone(
            str(calendar_meta.get("timeZone") or self.config.default_timezone)
        )
        raw_items_value = payload.get("items") if isinstance(payload, Mapping) else []
        raw_items: list[Any] = (
            raw_items_value if isinstance(raw_items_value, list) else []
        )
        events = [
            event
            for raw in raw_items
            if isinstance(raw, Mapping)
            for event in [_normalise_event(raw, calendar_tz=calendar_tz)]
            if event is not None
        ]
        signals = _calendar_signals(
            events,
            now=self._now().astimezone(calendar_tz),
            window=window,
            workday_start=_parse_clock(self.config.workday_start),
            workday_end=_parse_clock(self.config.workday_end),
        )
        contributions: list[ExecutiveContextContribution] = [
            self._capability_status(request, status),
            self._schedule_summary(request, window, events, signals),
        ]
        contributions.extend(self._meeting(request, event) for event in events)
        if signals["conflict_count"]:
            contributions.append(
                self._signal(request, "calendar_conflict", signals["conflict_summary"])
            )
        if signals["longest_free_block_minutes"]:
            contributions.append(
                self._signal(request, "availability", signals["free_block_summary"])
            )
        if signals["preparation_count"]:
            contributions.append(
                self._signal(
                    request,
                    "preparation_requirement",
                    signals["preparation_summary"],
                )
            )
        return tuple(contributions)

    def _now(self) -> datetime:
        now = self.config.now()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now

    def _window_for_request(
        self,
        request: ExecutiveContextProviderRequest,
        tz: ZoneInfo,
    ) -> GoogleCalendarWindow:
        text = _normalise_text(request.turn.message).casefold()
        now = self._now().astimezone(tz)
        max_end = now + timedelta(days=self.config.max_range_days)
        if "next 24" in text or "24 hours" in text:
            return GoogleCalendarWindow(
                now, min(now + timedelta(hours=24), max_end), "next_24h"
            )
        if "next 7" in text or "week" in text:
            return GoogleCalendarWindow(
                now, min(now + timedelta(days=7), max_end), "next_7d"
            )
        if "tomorrow" in text:
            start = _day_start(now.date() + timedelta(days=1), tz)
            return GoogleCalendarWindow(
                start, min(start + timedelta(days=1), max_end), "tomorrow"
            )
        if "next meeting" in text or "next event" in text:
            return GoogleCalendarWindow(now, max_end, "next_event")
        start = _day_start(now.date(), tz)
        return GoogleCalendarWindow(
            start, min(start + timedelta(days=1), max_end), "today"
        )

    def _capability_status(
        self,
        request: ExecutiveContextProviderRequest,
        status: str,
    ) -> ExecutiveContextContribution:
        if status == "connected":
            summary = (
                "Google Calendar read-only context provider is connected; "
                "calendar writes and external execution remain unavailable."
            )
        elif status == "configured_awaiting_live_read_enablement":
            summary = (
                "Google Calendar context provider is installed but live reads are disabled; "
                "awaiting Calendar authorisation/review before reading events."
            )
        else:
            summary = (
                "Google Calendar context provider is awaiting Calendar authorisation; "
                "no calendar events were read."
            )
        return self._contribution(
            request,
            context_type="capability_status",
            title="Google Calendar read-only capability",
            summary=summary,
            payload={
                "trace_category": "google_calendar_status",
                "status": status,
                "execution_boundary": EXECUTION_BOUNDARY,
                "writes_supported": False,
            },
            record_key=f"status:{status}",
            tags=("google_calendar", "read_only", "no_execution"),
        )

    def _schedule_summary(
        self,
        request: ExecutiveContextProviderRequest,
        window: GoogleCalendarWindow,
        events: list[CalendarEvent],
        signals: Mapping[str, Any],
    ) -> ExecutiveContextContribution:
        summary = (
            f"Calendar window={window.label}; meetings={len(events)}; "
            f"scheduled_minutes={signals['scheduled_minutes']}; "
            f"next meeting={signals['next_meeting_label']}; "
            f"conflicts={signals['conflict_count']}; "
            f"longest free block={signals['longest_free_block_minutes']} minutes; "
            f"out-of-hours={signals['out_of_hours_count']}; "
            "execution_boundary=not_executed."
        )
        return self._contribution(
            request,
            context_type="schedule_summary",
            title="Google Calendar schedule summary",
            summary=summary,
            payload={
                "trace_category": "google_calendar_summary",
                "window": window.label,
            },
            record_key=f"summary:{window.label}:{len(events)}:{signals['scheduled_minutes']}",
            tags=("google_calendar", "schedule_summary", "read_only"),
        )

    def _meeting(
        self,
        request: ExecutiveContextProviderRequest,
        event: CalendarEvent,
    ) -> ExecutiveContextContribution:
        summary = (
            f"{event.title}; start={event.start_label}; end={event.end_label}; "
            f"status={event.response_status}; attendees={event.attendee_count}; "
            f"external_attendees={event.external_attendee_count}; "
            f"all_day={event.all_day}; sensitivity={event.sensitivity}."
        )
        return self._contribution(
            request,
            context_type="meeting",
            title="Google Calendar meeting",
            summary=summary,
            payload={
                "trace_category": "google_calendar_event",
                "event_digest": event.event_digest,
                "execution_boundary": EXECUTION_BOUNDARY,
            },
            record_key=f"event:{event.event_digest}",
            tags=("google_calendar", "meeting", "read_only"),
        )

    def _signal(
        self,
        request: ExecutiveContextProviderRequest,
        context_type: str,
        summary: str,
    ) -> ExecutiveContextContribution:
        return self._contribution(
            request,
            context_type=context_type,
            title=f"Google Calendar {context_type.replace('_', ' ')}",
            summary=f"{summary} execution_boundary=not_executed.",
            payload={"trace_category": f"google_calendar_{context_type}"},
            record_key=f"{context_type}:{_digest(summary)[:12]}",
            tags=("google_calendar", context_type, "read_only"),
        )

    def _contribution(
        self,
        request: ExecutiveContextProviderRequest,
        *,
        context_type: str,
        title: str,
        summary: str,
        payload: Mapping[str, Any],
        record_key: str,
        tags: tuple[str, ...],
    ) -> ExecutiveContextContribution:
        observed_at = (
            self._now().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        source_ref = f"google_calendar:{_digest(record_key)[:16]}"
        evidence = ContextEvidenceReference(
            evidence_id=source_ref,
            source_provider_id=self.metadata.provider_id,
            source_mechanism=self.metadata.source_mechanism,
            source_record_ref=source_ref,
            observed_at=observed_at,
            digest=_digest(f"{context_type}:{summary}")[:16],
        )
        return ExecutiveContextContribution(
            contribution_id=source_ref,
            context_type=context_type,
            title=title,
            summary=_safe_label(summary, limit=800),
            payload=payload,
            source_provider_id=self.metadata.provider_id,
            source_mechanism=self.metadata.source_mechanism,
            source_record_ref=source_ref,
            observed_at=observed_at,
            confidence=0.95,
            freshness_state="current",
            sensitivity="private",
            tenant_id=request.turn.tenant_id,
            user_id=request.turn.actor_id,
            evidence_refs=(evidence,),
            tags=tags,
        )


@dataclass(frozen=True)
class CalendarEvent:
    event_digest: str
    title: str
    start: datetime
    end: datetime
    all_day: bool
    response_status: str
    attendee_count: int
    external_attendee_count: int
    sensitivity: str

    @property
    def start_label(self) -> str:
        return self.start.strftime("%Y-%m-%d %H:%M %Z")

    @property
    def end_label(self) -> str:
        return self.end.strftime("%Y-%m-%d %H:%M %Z")


def _normalise_event(
    raw: Mapping[str, Any], *, calendar_tz: ZoneInfo
) -> CalendarEvent | None:
    if str(raw.get("status") or "").casefold() == "cancelled":
        return None
    attendees_value = raw.get("attendees")
    attendees: list[Any] = attendees_value if isinstance(attendees_value, list) else []
    self_response = ""
    attendee_count = 0
    external_count = 0
    for attendee in attendees:
        if not isinstance(attendee, Mapping):
            continue
        attendee_count += 1
        if not attendee.get("self"):
            external_count += 1
        if attendee.get("self"):
            self_response = str(attendee.get("responseStatus") or "")
    if self_response.casefold() == "declined":
        return None
    start_value = raw.get("start")
    end_value = raw.get("end")
    start_raw: Mapping[str, Any] = (
        start_value if isinstance(start_value, Mapping) else {}
    )
    end_raw: Mapping[str, Any] = end_value if isinstance(end_value, Mapping) else {}
    start, all_day = _parse_event_time(start_raw, calendar_tz=calendar_tz)
    end, _ = _parse_event_time(
        end_raw, calendar_tz=calendar_tz, default_date=start.date()
    )
    if end <= start:
        end = start + timedelta(
            days=1 if all_day else 0, minutes=30 if not all_day else 0
        )
    visibility = str(raw.get("visibility") or "").casefold()
    private = visibility == "private"
    title = (
        "Private calendar event"
        if private
        else _safe_label(str(raw.get("summary") or "Untitled calendar event"))
    )
    response_status = _safe_label(
        self_response or str(raw.get("status") or "confirmed"), limit=40
    )
    event_id = str(raw.get("id") or raw.get("iCalUID") or title)
    return CalendarEvent(
        event_digest=_digest(f"{event_id}:{start.isoformat()}:{end.isoformat()}")[:16],
        title=title,
        start=start,
        end=end,
        all_day=all_day,
        response_status=response_status,
        attendee_count=attendee_count,
        external_attendee_count=external_count,
        sensitivity="private" if private else "internal",
    )


def _parse_event_time(
    payload: Mapping[str, Any],
    *,
    calendar_tz: ZoneInfo,
    default_date: date | None = None,
) -> tuple[datetime, bool]:
    if payload.get("dateTime"):
        value = datetime.fromisoformat(str(payload["dateTime"]).replace("Z", "+00:00"))
        return value.astimezone(calendar_tz), False
    value_date = date.fromisoformat(str(payload.get("date") or default_date))
    return _day_start(value_date, calendar_tz), True


def _timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _day_start(value: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(value, dt_time.min, tzinfo=tz)


def _parse_clock(value: str) -> dt_time:
    hour, minute = (int(part) for part in value.split(":", 1))
    return dt_time(hour=hour, minute=minute)


def _calendar_signals(
    events: list[CalendarEvent],
    *,
    now: datetime,
    window: GoogleCalendarWindow,
    workday_start: dt_time,
    workday_end: dt_time,
) -> dict[str, Any]:
    timed = sorted(
        (event for event in events if not event.all_day), key=lambda item: item.start
    )
    next_meeting = next((event for event in timed if event.end >= now), None)
    scheduled_minutes = sum(
        max(0, int((event.end - event.start).total_seconds() // 60)) for event in timed
    )
    conflict_count = sum(
        1
        for previous, current in zip(timed, timed[1:], strict=False)
        if current.start < previous.end
    )
    out_of_hours = [
        event
        for event in timed
        if event.start.timetz().replace(tzinfo=None) < workday_start
        or event.end.timetz().replace(tzinfo=None) > workday_end
    ]
    prep_events = [
        event
        for event in timed
        if event.external_attendee_count
        or re.search(
            r"\b(strategy|stakeholder|partnership|government|board|investor|franchise|review)\b",
            event.title.casefold(),
        )
    ]
    free_minutes = _longest_free_block_minutes(
        timed,
        day_start=datetime.combine(
            window.start.date(), workday_start, tzinfo=window.start.tzinfo
        ),
        day_end=datetime.combine(
            window.start.date(), workday_end, tzinfo=window.start.tzinfo
        ),
    )
    return {
        "next_meeting_label": next_meeting.title if next_meeting else "none",
        "scheduled_minutes": scheduled_minutes,
        "conflict_count": conflict_count,
        "conflict_summary": f"Calendar conflict signal: {conflict_count} overlapping meeting pair(s) detected.",
        "longest_free_block_minutes": free_minutes,
        "free_block_summary": f"Calendar availability signal: longest free block is {free_minutes} minutes.",
        "out_of_hours_count": len(out_of_hours),
        "preparation_count": len(prep_events),
        "preparation_summary": f"Calendar preparation signal: {len(prep_events)} meeting(s) may need preparation.",
    }


def _longest_free_block_minutes(
    events: list[CalendarEvent],
    *,
    day_start: datetime,
    day_end: datetime,
) -> int:
    cursor = day_start
    longest = 0
    for event in events:
        start = max(event.start, day_start)
        end = min(event.end, day_end)
        if end <= day_start or start >= day_end:
            continue
        if start > cursor:
            longest = max(longest, int((start - cursor).total_seconds() // 60))
        if end > cursor:
            cursor = end
    if day_end > cursor:
        longest = max(longest, int((day_end - cursor).total_seconds() // 60))
    return max(0, longest)
