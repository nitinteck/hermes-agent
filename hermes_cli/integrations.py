"""Operator-safe Hermes integration framework diagnostics."""

from __future__ import annotations

import json
from typing import Any

from gateway.google_calendar_context_provider import (
    GoogleCalendarProviderConfig,
    build_google_calendar_integration_service,
    google_calendar_capability_status,
)


def integration_status() -> dict[str, Any]:
    config = GoogleCalendarProviderConfig.from_environment()
    service = build_google_calendar_integration_service(config)
    integrations = [
        {
            "integration_id": definition.integration_id,
            "display_name": definition.display_name,
            "integration_type": definition.integration_type,
            "version": definition.version,
            "environment": definition.environment,
            "lifecycle_state": definition.lifecycle_state,
        }
        for definition in service.connection_registry.list_integrations()
    ]
    connections = [
        connection.safe_trace()
        for connection in service.connection_registry.list_by_integration(
            "google_calendar"
        )
    ]
    capabilities = [
        capability.safe_trace() for capability in service.capability_registry.list_all()
    ]
    adapters = [adapter.safe_trace() for adapter in service.adapter_registry.list_all()]
    return {
        "status": "ok",
        "framework": "hermes_integration_and_connection_framework_v1",
        "external_execution": "not_executed",
        "live_execution_enabled": False,
        "outbound_writes_enabled": False,
        "integrations": integrations,
        "connections": connections,
        "capabilities": capabilities,
        "adapters": adapters,
        "google_calendar_authorisation_status": google_calendar_capability_status(
            config
        ),
        "redacted": True,
    }


def cmd_status(args: Any) -> None:
    del args
    print(json.dumps(integration_status(), sort_keys=True))


def register_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "integrations",
        help="Inspect operator-safe integration and connection state",
    )
    parser.set_defaults(func=cmd_status)
    subs = parser.add_subparsers(dest="integrations_command")
    status = subs.add_parser("status", help="Show integration framework status")
    status.set_defaults(func=cmd_status)
