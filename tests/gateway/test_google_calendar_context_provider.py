from __future__ import annotations

from datetime import datetime, timezone
import json

from gateway.executive_orchestrator import ExecutiveContextLimits, ExecutiveTurnInput
from gateway.executive_context_providers import (
    ExecutiveContextCollectionService,
    ExecutiveContextProviderRegistry,
)
from gateway.google_calendar_context_provider import (
    GoogleCalendarContextProvider,
    GoogleCalendarProviderConfig,
    GoogleCalendarWindow,
    should_select_google_calendar_context,
)


def _turn(message: str) -> ExecutiveTurnInput:
    return ExecutiveTurnInput(
        tenant_id="tenant-1",
        conversation_id="conversation-1",
        actor_id="user-1",
        actor_name="Nitin",
        platform="local_diagnostic",
        chat_id=None,
        message=message,
        session_id="session-1",
        session_key="local:session-1:user-1",
    )


class FakeCalendarClient:
    def __init__(self, *, events: list[dict] | None = None) -> None:
        self.events = events or []
        self.calls: list[dict] = []

    def get_primary_calendar(self) -> dict:
        return {"id": "primary", "summary": "Nitin", "timeZone": "Europe/London"}

    def list_events(
        self, *, calendar_id: str, window: GoogleCalendarWindow, max_results: int
    ) -> dict:
        self.calls.append({
            "calendar_id": calendar_id,
            "time_min": window.start.isoformat(),
            "time_max": window.end.isoformat(),
            "max_results": max_results,
        })
        return {"items": self.events}


def test_disconnected_provider_returns_safe_capability_status_without_live_read(
    monkeypatch,
) -> None:
    monkeypatch.delenv("HERMES_GOOGLE_CALENDAR_TOKEN_FILE", raising=False)
    monkeypatch.delenv("HERMES_GOOGLE_CALENDAR_CLIENT_SECRET_FILE", raising=False)
    provider = GoogleCalendarContextProvider(
        config=GoogleCalendarProviderConfig(
            provider_enabled=True,
            live_reads_enabled=True,
            now=lambda: datetime(2026, 7, 29, 9, 30, tzinfo=timezone.utc),
        )
    )

    contributions = provider.collect(
        _request("What meetings do I have today?", provider)
    )

    assert len(contributions) == 1
    assert contributions[0].context_type == "capability_status"
    assert "awaiting Calendar authorisation" in contributions[0].summary
    rendered = json.dumps(contributions[0].safe_trace()).casefold()
    assert "token" not in rendered
    assert "secret" not in rendered


def test_calendar_selection_only_runs_for_calendar_context_requests() -> None:
    assert should_select_google_calendar_context(
        "What meetings do I have today?", "executive_status"
    )
    assert should_select_google_calendar_context(
        "Give me today's brief with my agenda", "daily_brief"
    )
    assert not should_select_google_calendar_context(
        "Should we add read-only Gmail before Calendar?", "decision_support"
    )
    assert not should_select_google_calendar_context(
        "Create a calendar event for tomorrow", "potentially_executable"
    )
    assert not should_select_google_calendar_context(
        "Explain the Executive Orchestrator architecture", "ordinary_conversation"
    )


def test_collection_service_selects_calendar_provider_only_when_needed() -> None:
    registry = ExecutiveContextProviderRegistry()
    calendar = GoogleCalendarContextProvider(
        config=GoogleCalendarProviderConfig(
            provider_enabled=True, live_reads_enabled=False
        )
    )
    registry.register(calendar)
    service = ExecutiveContextCollectionService(registry=registry)

    selected = service.collect(
        turn=_turn("What meetings do I have today?"),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(max_context_chars=1200),
    )
    unrelated = service.collect(
        turn=_turn("What should I use you for right now?"),
        request_classification="ordinary_conversation",
        limits=ExecutiveContextLimits(max_context_chars=1200),
    )

    assert "google_calendar_context" in selected.selected_provider_ids
    assert "google_calendar_context" not in unrelated.selected_provider_ids


def test_normalises_events_without_descriptions_attendee_emails_or_raw_google_payload() -> (
    None
):
    client = FakeCalendarClient(
        events=[
            {
                "id": "evt-1",
                "summary": "Partnership review",
                "description": "private notes with token=secret",
                "location": "OVG HQ",
                "status": "confirmed",
                "start": {"dateTime": "2026-07-29T10:00:00+01:00"},
                "end": {"dateTime": "2026-07-29T10:30:00+01:00"},
                "attendees": [
                    {
                        "email": "nitin@example.com",
                        "self": True,
                        "responseStatus": "accepted",
                    },
                    {"email": "partner@example.org", "responseStatus": "needsAction"},
                ],
                "organizer": {"email": "partner@example.org"},
            },
            {
                "id": "evt-cancelled",
                "summary": "Cancelled event",
                "status": "cancelled",
                "start": {"dateTime": "2026-07-29T11:00:00+01:00"},
                "end": {"dateTime": "2026-07-29T12:00:00+01:00"},
            },
            {
                "id": "evt-declined",
                "summary": "Declined event",
                "status": "confirmed",
                "start": {"dateTime": "2026-07-29T13:00:00+01:00"},
                "end": {"dateTime": "2026-07-29T14:00:00+01:00"},
                "attendees": [
                    {
                        "email": "nitin@example.com",
                        "self": True,
                        "responseStatus": "declined",
                    }
                ],
            },
        ]
    )
    provider = GoogleCalendarContextProvider(
        config=GoogleCalendarProviderConfig(
            provider_enabled=True,
            live_reads_enabled=True,
            credential_status_override="connected",
            now=lambda: datetime(2026, 7, 29, 8, 30, tzinfo=timezone.utc),
        ),
        client=client,
    )

    snapshot = _collection_with_provider(provider, "What meetings do I have today?")
    rendered_context = snapshot.composed_context
    rendered_trace = json.dumps(snapshot.safe_trace_metadata())

    assert snapshot.contribution_counts_by_type["meeting"] == 1
    assert snapshot.contribution_counts_by_type["schedule_summary"] == 1
    assert "Partnership review" in rendered_context
    assert "private notes" not in rendered_context
    assert "partner@example.org" not in rendered_context
    assert "evt-1" not in rendered_context
    assert "private notes" not in rendered_trace
    assert "partner@example.org" not in rendered_trace
    assert "evt-1" not in rendered_trace


def test_calendar_signals_include_next_meeting_gaps_conflicts_and_prep() -> None:
    client = FakeCalendarClient(
        events=[
            {
                "id": "evt-a",
                "summary": "Stakeholder prep",
                "status": "confirmed",
                "start": {"dateTime": "2026-07-29T10:00:00+01:00"},
                "end": {"dateTime": "2026-07-29T11:00:00+01:00"},
                "attendees": [
                    {"email": "external@example.org", "responseStatus": "accepted"}
                ],
            },
            {
                "id": "evt-b",
                "summary": "Overlap",
                "status": "tentative",
                "start": {"dateTime": "2026-07-29T10:30:00+01:00"},
                "end": {"dateTime": "2026-07-29T11:30:00+01:00"},
            },
            {
                "id": "evt-c",
                "summary": "Late call",
                "status": "confirmed",
                "start": {"dateTime": "2026-07-29T18:00:00+01:00"},
                "end": {"dateTime": "2026-07-29T19:00:00+01:00"},
            },
        ]
    )
    provider = GoogleCalendarContextProvider(
        config=GoogleCalendarProviderConfig(
            provider_enabled=True,
            live_reads_enabled=True,
            credential_status_override="connected",
            now=lambda: datetime(2026, 7, 29, 8, 0, tzinfo=timezone.utc),
        ),
        client=client,
    )

    snapshot = _collection_with_provider(
        provider, "Where are my conflicts and free blocks today?"
    )
    context = snapshot.composed_context.casefold()

    assert "next meeting" in context
    assert "conflict" in context
    assert "longest free block" in context
    assert "out-of-hours" in context
    assert "preparation" in context
    assert client.calls[0]["max_results"] == 25


def _request(message: str, provider: GoogleCalendarContextProvider):
    from gateway.executive_context_providers import ExecutiveContextProviderRequest

    return ExecutiveContextProviderRequest(
        turn=_turn(message),
        request_classification="executive_status",
        required_context_types=provider.metadata.supported_context_types,
        limits=ExecutiveContextLimits(max_context_chars=3000),
    )


def _collection_with_provider(
    provider: GoogleCalendarContextProvider,
    message: str,
):
    registry = ExecutiveContextProviderRegistry()
    registry.register(provider)
    service = ExecutiveContextCollectionService(registry=registry)
    return service.collect(
        turn=_turn(message),
        request_classification="executive_status",
        limits=ExecutiveContextLimits(max_context_chars=3000),
    )
