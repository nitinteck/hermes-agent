"""Operator-safe Executive Orchestrator diagnostics."""

from __future__ import annotations

import json
import os
import uuid
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


def cmd_status(args: Any) -> None:
    del args
    print(json.dumps(executive_orchestrator_status(), sort_keys=True))


def cmd_diagnostic_turn(args: Any) -> None:
    prompt = " ".join(getattr(args, "message", None) or ()).strip()
    if not prompt:
        prompt = "Hermes executive orchestrator diagnostic. Reply with a short health acknowledgement."
    print(json.dumps(run_local_diagnostic_turn(prompt), sort_keys=True))


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
