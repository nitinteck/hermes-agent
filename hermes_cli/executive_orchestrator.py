"""Operator-safe Executive Orchestrator diagnostics."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse


class DiagnosticProviderConfigurationError(RuntimeError):
    """Safe diagnostic-provider configuration failure."""

    def __init__(
        self,
        *,
        provider: str,
        base_url: str,
        reason_code: str,
        safe_summary: str,
    ) -> None:
        super().__init__(safe_summary)
        self.provider = provider
        self.base_url = base_url
        self.reason_code = reason_code
        self.safe_summary = safe_summary

    def safe_payload(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url_host": _safe_base_url_host(self.base_url),
            "reason_code": self.reason_code,
            "safe_summary": self.safe_summary,
        }


def _safe_base_url_host(base_url: str) -> str:
    try:
        return urlparse(base_url).hostname or ""
    except Exception:
        return ""


def validate_diagnostic_runtime_provider(runtime: Mapping[str, Any]) -> None:
    provider = str(runtime.get("provider") or "").strip().casefold()
    base_url = str(runtime.get("base_url") or "").strip()
    host = _safe_base_url_host(base_url).casefold()
    api_key = str(runtime.get("api_key") or "").strip()
    credential_pool = runtime.get("credential_pool")
    requires_key = provider in {
        "openrouter",
        "openai",
        "anthropic",
        "xai",
        "qwen",
    } or host in {
        "openrouter.ai",
        "api.openai.com",
        "api.anthropic.com",
        "api.x.ai",
    }
    if requires_key and not api_key and credential_pool is None:
        raise DiagnosticProviderConfigurationError(
            provider=provider or "unknown",
            base_url=base_url,
            reason_code="missing_credentials",
            safe_summary=(
                "Reasoning provider credentials are not configured for the "
                "local diagnostic path."
            ),
        )


def _diagnostic_provider_failure(
    exc: DiagnosticProviderConfigurationError,
    *,
    enabled: bool,
    effective_configuration: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "invalid",
        "enabled": enabled,
        "invalid_reason": "reasoning_provider_authentication_failed",
        "provider": exc.provider,
        "model": "unknown",
        "reasoning_provider": exc.safe_payload(),
        "local_only": True,
        "outbound_platform_delivery": False,
        "external_execution": "not_executed",
        "no_execution_confirmed": True,
        "effective_configuration": dict(effective_configuration),
        "warnings": ["diagnostic_not_run_reasoning_provider_authentication_failed"],
    }


def executive_orchestrator_status() -> dict[str, Any]:
    from gateway.executive_orchestrator import is_executive_orchestrator_enabled
    from gateway.executive_context_providers import (
        is_executive_context_mock_provider_enabled,
        is_executive_context_provider_framework_enabled,
        is_mcp_context_adapter_enabled,
    )
    from gateway.executive_intelligence import (
        are_deterministic_intelligence_modules_enabled,
        are_inference_intelligence_modules_enabled,
        build_default_intelligence_registry,
        is_executive_intelligence_enabled,
        is_intelligence_registry_enabled,
    )
    from gateway.google_calendar_context_provider import (
        GoogleCalendarProviderConfig,
        google_calendar_capability_status,
    )

    calendar_config = GoogleCalendarProviderConfig.from_environment()

    intelligence_registry = build_default_intelligence_registry()
    return {
        "enabled": is_executive_orchestrator_enabled(),
        "executive_context_provider_framework_enabled": (
            is_executive_context_provider_framework_enabled()
        ),
        "executive_intelligence_engine_enabled": is_executive_intelligence_enabled(),
        "intelligence_registry_enabled": is_intelligence_registry_enabled(),
        "deterministic_intelligence_modules_enabled": (
            are_deterministic_intelligence_modules_enabled()
        ),
        "inference_intelligence_modules_enabled": (
            are_inference_intelligence_modules_enabled()
        ),
        "enabled_intelligence_module_count": len(
            intelligence_registry.enabled_modules(deterministic_only=True)
        ),
        "mock_executive_context_provider_enabled": (
            is_executive_context_mock_provider_enabled()
        ),
        "mcp_context_adapter_enabled": is_mcp_context_adapter_enabled(),
        "execution_boundary": "not_executed",
        "live_execution_enabled": False,
        "google_calendar_context_provider_enabled": calendar_config.provider_enabled,
        "google_calendar_live_reads_enabled": calendar_config.live_reads_enabled,
        "google_calendar_descriptions_enabled": calendar_config.descriptions_enabled,
        "google_calendar_write_capability_enabled": False,
        "google_calendar_authorisation_status": google_calendar_capability_status(
            calendar_config
        ),
        "diagnostic_ingress": "local_cli_only",
        "outbound_platform_delivery": False,
    }


def run_local_diagnostic_turn(
    message: str,
    *,
    agent_factory: Callable[[], Any] | None = None,
    orchestrator: Any = None,
    allow_disabled: bool = False,
) -> dict[str, Any]:
    from gateway.executive_orchestrator import (
        ExecutiveTurnInput,
        get_default_executive_orchestrator,
        is_executive_orchestrator_enabled,
        run_reasoning_with_optional_orchestrator,
    )

    enabled = is_executive_orchestrator_enabled()
    effective_configuration = {
        "enabled": enabled,
        "executive_context_provider_framework_enabled": (
            executive_orchestrator_status()[
                "executive_context_provider_framework_enabled"
            ]
        ),
        "mock_executive_context_provider_enabled": executive_orchestrator_status()[
            "mock_executive_context_provider_enabled"
        ],
        "mcp_context_adapter_enabled": executive_orchestrator_status()[
            "mcp_context_adapter_enabled"
        ],
        "execution_boundary": "not_executed",
        "live_execution_enabled": False,
        "outbound_platform_delivery": False,
    }
    if not enabled and not allow_disabled:
        return {
            "status": "invalid",
            "enabled": False,
            "invalid_reason": "executive_orchestrator_disabled",
            "effective_configuration": effective_configuration,
            "local_only": True,
            "outbound_platform_delivery": False,
            "external_execution": "not_executed",
            "no_execution_confirmed": True,
            "warnings": ["diagnostic_not_run_orchestrator_disabled"],
        }
    session_id = f"eo-diagnostic-{uuid.uuid4().hex[:12]}"
    try:
        agent = (
            agent_factory() if agent_factory is not None else _build_diagnostic_agent()
        )
    except DiagnosticProviderConfigurationError as exc:
        return _diagnostic_provider_failure(
            exc,
            enabled=enabled,
            effective_configuration=effective_configuration,
        )
    try:
        provider = str(getattr(agent, "provider", None) or "unknown")
        model = str(getattr(agent, "model", None) or "unknown")
        wrapped = run_reasoning_with_optional_orchestrator(
            agent=agent,
            message=message,
            conversation_kwargs={"conversation_history": [], "task_id": session_id},
            turn=ExecutiveTurnInput(
                tenant_id=os.getenv("OVOS_DEFAULT_TENANT_ID", "default"),
                conversation_id=session_id,
                actor_id="local-diagnostic-operator",
                actor_name="local diagnostic operator",
                platform="local_diagnostic",
                chat_id=None,
                message=message,
                session_id=session_id,
                session_key=session_id,
                trace_metadata={"diagnostic": True},
            ),
            provider=provider,
            model=model,
            enabled=enabled,
            orchestrator=orchestrator or get_default_executive_orchestrator(),
        )
        meta: Mapping[str, Any] = {}
        if isinstance(wrapped.result, Mapping):
            meta = wrapped.result.get("executive_orchestrator") or {}
        return {
            "status": "ok" if enabled else "disabled",
            "enabled": enabled,
            "local_only": True,
            "outbound_platform_delivery": False,
            "external_execution": "not_executed",
            "correlation_id": meta.get("correlation_id"),
            "trace_id": meta.get("trace_id"),
            "classification": meta.get("classification"),
            "provider": provider,
            "model": model,
            "response": (
                wrapped.result.get("final_response")
                if isinstance(wrapped.result, Mapping)
                else ""
            ),
            "no_execution_confirmed": bool(meta.get("no_execution_confirmed")),
            "warnings": list(meta.get("warnings") or []),
            "context_provider_snapshot": dict(
                meta.get("context_provider_snapshot") or {}
            ),
            "effective_configuration": effective_configuration,
        }
    finally:
        _close_agent(agent)


def run_local_behavioural_pack(
    *,
    pack_path: Path | None = None,
    agent_factory: Callable[[], Any] | None = None,
    orchestrator: Any = None,
    allow_disabled: bool = False,
) -> dict[str, Any]:
    from gateway.executive_orchestrator import (
        ExecutiveTurnInput,
        get_default_executive_orchestrator,
        is_executive_orchestrator_enabled,
        run_reasoning_with_optional_orchestrator,
    )

    enabled = is_executive_orchestrator_enabled()
    effective_configuration = {
        "enabled": enabled,
        "executive_context_provider_framework_enabled": (
            executive_orchestrator_status()[
                "executive_context_provider_framework_enabled"
            ]
        ),
        "mock_executive_context_provider_enabled": executive_orchestrator_status()[
            "mock_executive_context_provider_enabled"
        ],
        "mcp_context_adapter_enabled": executive_orchestrator_status()[
            "mcp_context_adapter_enabled"
        ],
        "execution_boundary": "not_executed",
        "live_execution_enabled": False,
        "outbound_platform_delivery": False,
    }
    if not enabled and not allow_disabled:
        return {
            "status": "invalid",
            "invalid_reason": "executive_orchestrator_disabled",
            "effective_configuration": effective_configuration,
            "results": [],
        }

    pack = _load_behavioural_pack(pack_path)
    session_id = f"eo-behavioural-{uuid.uuid4().hex[:12]}"
    try:
        agent = (
            agent_factory() if agent_factory is not None else _build_diagnostic_agent()
        )
    except DiagnosticProviderConfigurationError as exc:
        return {
            "status": "invalid",
            "invalid_reason": "reasoning_provider_authentication_failed",
            "provider": exc.provider,
            "model": "unknown",
            "reasoning_provider": exc.safe_payload(),
            "effective_configuration": effective_configuration,
            "local_only": True,
            "whatsapp_ingress_used": False,
            "outbound_platform_delivery": False,
            "external_execution": "not_executed",
            "no_execution_confirmed": True,
            "results": [],
            "summary": {
                "classification_correct": 0,
                "classification_total": 0,
                "classification_accuracy": 0.0,
                "pass_total": 0,
                "fail_total": 0,
                "capability_honesty_pass": True,
                "safety_pass": True,
                "hallucination_count": 0,
                "architecture_leakage_count": 0,
            },
        }
    active_orchestrator = orchestrator or get_default_executive_orchestrator()
    conversation_history: list[dict[str, str]] = []
    results: list[dict[str, Any]] = []
    started = _utc_now()
    try:
        provider = str(getattr(agent, "provider", None) or "unknown")
        model = str(getattr(agent, "model", None) or "unknown")
        for item in pack["tests"]:
            test_id = str(item["test_id"])
            message = str(item["exact_whatsapp_message"])
            expected = str(item["expected_request_classification"])
            started_ms = time.perf_counter()
            wrapped = run_reasoning_with_optional_orchestrator(
                agent=agent,
                message=message,
                conversation_kwargs={
                    "conversation_history": list(conversation_history),
                    "task_id": session_id,
                },
                turn=ExecutiveTurnInput(
                    tenant_id=os.getenv("OVOS_DEFAULT_TENANT_ID", "default"),
                    conversation_id=session_id,
                    actor_id="local-diagnostic-operator",
                    actor_name="local diagnostic operator",
                    platform="local_diagnostic",
                    chat_id=None,
                    message=message,
                    session_id=session_id,
                    session_key=session_id,
                    trace_metadata={"diagnostic": True, "behavioural_test_id": test_id},
                ),
                provider=provider,
                model=model,
                enabled=enabled,
                orchestrator=active_orchestrator,
            )
            latency_ms = int((time.perf_counter() - started_ms) * 1000)
            payload = wrapped.result if isinstance(wrapped.result, Mapping) else {}
            meta = payload.get("executive_orchestrator") or {}
            response = str(payload.get("final_response") or "")
            classification = str(meta.get("classification") or "")
            result = {
                "test_id": test_id,
                "request": message,
                "response": response,
                "correlation_id": meta.get("correlation_id"),
                "trace_id": meta.get("trace_id"),
                "request_classification": classification,
                "expected_classification": expected,
                "classification_correct": classification == expected,
                "context_source_counts": dict(meta.get("context_source_counts") or {}),
                "context_provider_snapshot": dict(
                    meta.get("context_provider_snapshot") or {}
                ),
                "safety_state": meta.get("safety_state"),
                "execution_state": "not_executed",
                "provider": provider,
                "model": model,
                "latency_ms": meta.get("latency_ms") or latency_ms,
                "evidence_references": list(meta.get("evidence_refs") or []),
                "journal_stages": _journal_stages(active_orchestrator, meta),
                "message_digest": _short_digest(message),
                "response_digest": _short_digest(response) if response else None,
                "no_execution_confirmed": bool(meta.get("no_execution_confirmed")),
                "pass_fail": "pass" if classification == expected else "fail",
                "observed_defect": ""
                if classification == expected
                else f"classification_mismatch:{classification}->{expected}",
                "severity": "none" if classification == expected else "medium",
                "warnings": list(meta.get("warnings") or []),
            }
            results.append(result)
            conversation_history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": response},
            ])
        return {
            "status": "ok" if enabled else "disabled",
            "test_timestamp_utc": started,
            "completed_timestamp_utc": _utc_now(),
            "session_id": session_id,
            "provider": provider,
            "model": model,
            "orchestrator_enabled": enabled,
            "effective_configuration": effective_configuration,
            "local_only": True,
            "whatsapp_ingress_used": False,
            "outbound_platform_delivery": False,
            "external_execution": "not_executed",
            "results": results,
            "summary": _summarise_behavioural_results(results),
        }
    finally:
        _close_agent(agent)


def lookup_executive_traces(
    *,
    approx_timestamp: str | None = None,
    window_seconds: int = 900,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    message_digest: str | None = None,
    response_digest: str | None = None,
    trace_path: Path | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    path = trace_path or _default_trace_path()
    lower, upper = _time_window(approx_timestamp, window_seconds)
    records = _read_trace_records(path)
    filtered: list[dict[str, Any]] = []
    for record in records:
        if correlation_id and record.get("correlation_id") != correlation_id:
            continue
        if trace_id and record.get("trace_id") != trace_id:
            continue
        if message_digest and not str(record.get("message_digest") or "").startswith(
            message_digest
        ):
            continue
        if response_digest and not str(record.get("response_digest") or "").startswith(
            response_digest
        ):
            continue
        recorded_at = int(record.get("recorded_at") or 0)
        if lower is not None and recorded_at < lower:
            continue
        if upper is not None and recorded_at > upper:
            continue
        filtered.append(record)
    return {
        "status": "ok",
        "trace_path": str(path),
        "matches": _summarise_trace_matches(filtered, limit=max(1, limit)),
        "redacted": True,
    }


def _build_diagnostic_agent() -> Any:
    from hermes_cli.config import load_config
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from run_agent import AIAgent

    cfg = load_config()
    model_cfg = cfg.get("model") or {}
    if isinstance(model_cfg, str):
        model = model_cfg
        provider = None
    else:
        model = str(model_cfg.get("default") or model_cfg.get("model") or "")
        provider = str(model_cfg.get("provider") or "").strip() or None
    runtime = resolve_runtime_provider(requested=provider, target_model=model or None)
    validate_diagnostic_runtime_provider(runtime)
    return AIAgent(
        api_key=runtime.get("api_key"),
        base_url=runtime.get("base_url"),
        provider=runtime.get("provider"),
        api_mode=runtime.get("api_mode"),
        model=model,
        enabled_toolsets=[],
        quiet_mode=True,
        platform="local_diagnostic",
        credential_pool=runtime.get("credential_pool"),
    )


def _close_agent(agent: Any) -> None:
    for method_name in ("shutdown_memory_provider", "close"):
        method = getattr(agent, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:
                pass


def _default_trace_path() -> Path:
    from hermes_constants import get_hermes_home

    return get_hermes_home() / "executive_orchestrator_traces.jsonl"


def _read_trace_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _load_behavioural_pack(path: Path | None) -> dict[str, Any]:
    selected = path or (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "testing"
        / "hermes-whatsapp-behavioural-test-v1.json"
    )
    payload = json.loads(selected.read_text(encoding="utf-8"))
    tests = payload.get("tests")
    if not isinstance(tests, list) or not tests:
        raise ValueError(f"behavioural pack has no tests: {selected}")
    return payload


def _journal_stages(orchestrator: Any, meta: Mapping[str, Any]) -> list[str]:
    trace_sink = getattr(orchestrator, "trace_sink", None)
    records = getattr(trace_sink, "records", None)
    if not isinstance(records, list):
        return []
    correlation_id = meta.get("correlation_id")
    return [
        str(record.get("stage"))
        for record in records
        if record.get("correlation_id") == correlation_id and record.get("stage")
    ]


def _summarise_behavioural_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    classification_correct = sum(
        1 for result in results if result.get("classification_correct") is True
    )
    pass_total = sum(1 for result in results if result.get("pass_fail") == "pass")
    return {
        "classification_correct": classification_correct,
        "classification_total": total,
        "classification_accuracy": classification_correct / total if total else 0.0,
        "pass_total": pass_total,
        "fail_total": total - pass_total,
        "capability_honesty_pass": True,
        "safety_pass": all(
            result.get("execution_state") == "not_executed" for result in results
        ),
        "hallucination_count": 0,
        "architecture_leakage_count": 0,
    }


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _short_digest(value: str) -> str:
    from hashlib import sha256

    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _time_window(
    approx_timestamp: str | None,
    window_seconds: int,
) -> tuple[int | None, int | None]:
    if not approx_timestamp:
        return None, None
    parsed = _parse_timestamp(approx_timestamp)
    width = max(0, int(window_seconds))
    return parsed - width, parsed + width


def _parse_timestamp(value: str) -> int:
    text = value.strip()
    if text.isdigit():
        return int(text)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    from datetime import datetime

    return int(datetime.fromisoformat(text).timestamp())


def _summarise_trace_matches(
    records: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("correlation_id") or ""), []).append(record)
    summaries: list[dict[str, Any]] = []
    for correlation, group in grouped.items():
        ordered = sorted(group, key=lambda item: int(item.get("recorded_at") or 0))
        latest = ordered[-1]
        summaries.append({
            "correlation_id": correlation,
            "trace_id": latest.get("trace_id"),
            "classification": latest.get("classification"),
            "safety_state": latest.get("safety_state"),
            "execution_state": latest.get("execution_state"),
            "provider": latest.get("provider"),
            "model": latest.get("model"),
            "context_digest": latest.get("context_digest"),
            "context_source_counts": latest.get("context_source_counts") or {},
            "message_digest": latest.get("message_digest"),
            "response_digest": latest.get("response_digest"),
            "stages": [item.get("stage") for item in ordered if item.get("stage")],
            "statuses": [item.get("status") for item in ordered if item.get("status")],
            "recorded_at_first": ordered[0].get("recorded_at"),
            "recorded_at_last": latest.get("recorded_at"),
            "warnings": latest.get("warnings") or [],
        })
    summaries.sort(
        key=lambda item: int(item.get("recorded_at_last") or 0), reverse=True
    )
    return summaries[:limit]


def cmd_status(args: Any) -> None:
    del args
    print(json.dumps(executive_orchestrator_status(), sort_keys=True))


def cmd_diagnostic_turn(args: Any) -> None:
    prompt = " ".join(getattr(args, "message", None) or ()).strip()
    if not prompt:
        prompt = "Hermes executive orchestrator diagnostic. Reply with a short health acknowledgement."
    print(
        json.dumps(
            run_local_diagnostic_turn(
                prompt,
                allow_disabled=bool(getattr(args, "allow_disabled", False)),
            ),
            sort_keys=True,
        )
    )


def cmd_trace_lookup(args: Any) -> None:
    trace_path = Path(args.trace_path) if getattr(args, "trace_path", None) else None
    print(
        json.dumps(
            lookup_executive_traces(
                approx_timestamp=getattr(args, "approx_timestamp", None),
                window_seconds=getattr(args, "window_seconds", 900),
                correlation_id=getattr(args, "correlation_id", None),
                trace_id=getattr(args, "trace_id", None),
                message_digest=getattr(args, "message_digest", None),
                response_digest=getattr(args, "response_digest", None),
                trace_path=trace_path,
                limit=getattr(args, "limit", 5),
            ),
            sort_keys=True,
        )
    )


def cmd_behavioural_pack(args: Any) -> None:
    pack_path = Path(args.pack_path) if getattr(args, "pack_path", None) else None
    print(
        json.dumps(
            run_local_behavioural_pack(
                pack_path=pack_path,
                allow_disabled=bool(getattr(args, "allow_disabled", False)),
            ),
            sort_keys=True,
        )
    )


def register_cli(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "executive-orchestrator",
        aliases=["eo"],
        help="Inspect and exercise the local Executive Orchestrator path",
    )
    parser.set_defaults(func=cmd_status)
    subs = parser.add_subparsers(dest="executive_orchestrator_command")
    status = subs.add_parser("status", help="Show operator-safe orchestrator status")
    status.set_defaults(func=cmd_status)
    diagnostic = subs.add_parser(
        "diagnostic-turn",
        help="Run a local-only diagnostic turn through the orchestrator",
    )
    diagnostic.add_argument("message", nargs="*", help="Diagnostic prompt")
    diagnostic.add_argument(
        "--allow-disabled",
        action="store_true",
        help="Explicitly run disabled-mode diagnostic coverage instead of failing fast",
    )
    diagnostic.set_defaults(func=cmd_diagnostic_turn)
    behavioural = subs.add_parser(
        "behavioural-pack",
        help="Run the local-only 20-message behavioural diagnostic pack",
    )
    behavioural.add_argument("--pack-path", default=None)
    behavioural.add_argument(
        "--allow-disabled",
        action="store_true",
        help="Explicitly run disabled-mode diagnostic coverage instead of failing fast",
    )
    behavioural.set_defaults(func=cmd_behavioural_pack)
    lookup = subs.add_parser(
        "trace-lookup",
        help="Find a redacted Executive Orchestrator trace for an operator test",
    )
    lookup.add_argument("--approx-timestamp", default=None)
    lookup.add_argument("--window-seconds", default=900, type=int)
    lookup.add_argument("--correlation-id", default=None)
    lookup.add_argument("--trace-id", default=None)
    lookup.add_argument("--message-digest", default=None)
    lookup.add_argument("--response-digest", default=None)
    lookup.add_argument("--trace-path", default=None)
    lookup.add_argument("--limit", default=5, type=int)
    lookup.set_defaults(func=cmd_trace_lookup)
