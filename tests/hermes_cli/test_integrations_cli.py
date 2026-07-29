from __future__ import annotations

import json

from hermes_cli.integrations import integration_status


def test_integration_status_is_operator_safe_and_non_executing(monkeypatch) -> None:
    monkeypatch.setenv("HERMES_GOOGLE_CALENDAR_CONTEXT_PROVIDER_ENABLED", "true")
    monkeypatch.setenv("HERMES_GOOGLE_CALENDAR_LIVE_READS_ENABLED", "false")
    monkeypatch.setenv("HERMES_GOOGLE_CALENDAR_TOKEN_FILE", "/tmp/secret-token.json")

    status = integration_status()
    rendered = json.dumps(status).casefold()

    assert status["status"] == "ok"
    assert status["framework"] == "hermes_integration_and_connection_framework_v1"
    assert status["external_execution"] == "not_executed"
    assert status["live_execution_enabled"] is False
    assert status["outbound_writes_enabled"] is False
    assert status["integrations"][0]["integration_id"] == "google_calendar"
    assert status["capabilities"][0]["read_write"] == "read"
    assert status["connections"][0]["status"] == "authorisation_required"
    assert status["redacted"] is True
    assert "secret-token" not in rendered
    assert "access_token" not in rendered
