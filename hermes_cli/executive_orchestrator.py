"""Operator-safe Executive Orchestrator diagnostics."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping


def executive_orchestrator_status() -> dict[str, Any]:
    from gateway.executive_orchestrator import is_executive_orchestrator_enabled

    return {
        "enabled": is_executive_orchestrator_enabled(),
        "execution_boundary": "not_executed",
        "live_execution_enabled": False,
        "diagnostic_ingress": "local_cli_only",
        "outbound_platform_delivery": False,
    }


def run_local_diagnostic_turn(
    message: str,
    *,
    agent_factory: Callable[[], Any] | None = None,
    orchestrator: Any = None,
) -> dict[str, Any]:
    from gateway.executive_orchestrator import (
        ExecutiveTurnInput,
        get_default_executive_orchestrator,
        is_executive_orchestrator_enabled,
        run_reasoning_with_optional_orchestrator,
    )

    enabled = is_executive_orchestrator_enabled()
    session_id = f"eo-diagnostic-{uuid.uuid4().hex[:12]}"
    agent = agent_factory() if agent_factory is not None else _build_diagnostic_agent()
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
    print(json.dumps(run_local_diagnostic_turn(prompt), sort_keys=True))


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
    diagnostic.set_defaults(func=cmd_diagnostic_turn)
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
