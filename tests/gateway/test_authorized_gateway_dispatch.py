"""Tests for the authorized_gateway_dispatch plugin hook."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import (
    AuthorizedGatewayEnvelope,
    MessageEvent,
    MessageType,
)
from gateway.session import SessionSource


def _make_event(text: str = "hello") -> MessageEvent:
    envelope = AuthorizedGatewayEnvelope(
        envelope_version=1,
        platform="whatsapp",
        transport="baileys",
        chat_id="synthetic-chat@example.invalid",
        chat_type="dm",
        source_message_id="message-1",
    )
    return MessageEvent(
        text=text,
        message_type=MessageType.DOCUMENT,
        message_id="message-1",
        media_urls=["/tmp/document.pdf"],
        media_types=["application/pdf"],
        metadata={"whatsapp_forwarded": True},
        raw_message={"fileName": "document.pdf", "timestamp": 123},
        authorized_envelope=envelope,
        constituent_envelopes=[envelope],
        reply_to_message_id="quoted-1",
        reply_to_text="quoted text",
        source=SessionSource(
            platform=Platform.WHATSAPP,
            user_id="15551234567@s.whatsapp.net",
            chat_id="15551234567@s.whatsapp.net",
            user_name="tester",
            chat_type="dm",
        ),
    )


def _make_runner():
    from gateway.run import GatewayRunner

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={Platform.WHATSAPP: PlatformConfig(enabled=True)}
    )
    runner.adapters = {Platform.WHATSAPP: SimpleNamespace(send=AsyncMock())}
    runner.pairing_store = MagicMock()
    runner.session_store = MagicMock()
    runner._running_agents = {}
    runner._update_prompt_pending = {}
    runner._is_user_authorized = MagicMock(return_value=True)
    runner._handle_message_with_agent = AsyncMock(return_value="agent-response")
    return runner


@pytest.mark.asyncio
async def test_hook_runs_after_authorization_with_complete_event(monkeypatch):
    event = _make_event()
    seen = {}

    async def _hook(name, **kwargs):
        assert name == "authorized_gateway_dispatch"
        seen["event"] = kwargs["event"]
        return [{"action": "respond", "text": "saved"}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _hook)
    runner = _make_runner()

    result = await runner._handle_message(event)

    runner._is_user_authorized.assert_called_once_with(event.source)
    assert seen["event"] is event
    assert seen["event"].media_urls == ["/tmp/document.pdf"]
    assert seen["event"].raw_message["fileName"] == "document.pdf"
    assert seen["event"].authorized_envelope is not None
    assert seen["event"].authorized_envelope.envelope_version == 1
    assert seen["event"].authorized_envelope.chat_id == "synthetic-chat@example.invalid"
    assert len(seen["event"].constituent_envelopes) == 1
    assert result == "saved"
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_hook_does_not_run_for_unauthorized_sender(monkeypatch):
    async_hook = AsyncMock(return_value=[{"action": "respond", "text": "unsafe"}])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", async_hook)
    runner = _make_runner()
    runner._is_user_authorized.return_value = False
    runner._get_unauthorized_dm_behavior = MagicMock(return_value="ignore")

    result = await runner._handle_message(_make_event())

    assert result is None
    async_hook.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["skip", "respond"])
async def test_terminal_actions_stop_dispatch(monkeypatch, action):
    payload = {"action": action, "text": "handled", "reason": "handled"}

    async def _hook(*args, **kwargs):
        return [payload, {"action": "rewrite", "text": "must-not-win"}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _hook)
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert result == ("handled" if action == "respond" else None)
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorized_hook_response_is_sanitized_before_visible_dispatch(
    monkeypatch,
):
    async def _hook(*args, **kwargs):
        return [{"action": "respond", "text": "Saved: My favourite colour is green."}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _hook)
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert result == "Got it. I'll remember My favourite colour is green."
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorized_hook_internal_payload_fails_open_to_normal_dispatch(
    monkeypatch,
):
    async def _hook(*args, **kwargs):
        return [
            {"action": "respond", "text": '{"event_type":"capture.saved","id":"CAP-1"}'}
        ]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _hook)
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert result == "agent-response"
    runner._handle_message_with_agent.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewrite_and_allow_continue_normal_dispatch(monkeypatch):
    results = iter([
        [{"action": "rewrite", "text": "rewritten"}],
        [{"action": "allow"}],
    ])

    async def _hook(*args, **kwargs):
        return next(results)

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _hook)
    runner = _make_runner()

    await runner._handle_message(_make_event("original"))
    assert runner._handle_message_with_agent.await_args.args[0].text == "rewritten"

    runner._handle_message_with_agent.reset_mock()
    await runner._handle_message(_make_event("original"))
    assert runner._handle_message_with_agent.await_args.args[0].text == "original"


@pytest.mark.asyncio
async def test_exception_and_timeout_fail_open(monkeypatch):
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    runner = _make_runner()

    async def _raising(*args, **kwargs):
        raise RuntimeError("contained")

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _raising)
    assert await runner._handle_message(_make_event()) == "agent-response"

    async def _slow(*args, **kwargs):
        await asyncio.sleep(1)
        return [{"action": "respond", "text": "late"}]

    async def _fast_timeout(awaitable, timeout):
        awaitable.close()
        raise TimeoutError

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook_async", _slow)
    monkeypatch.setattr("gateway.run.asyncio.wait_for", _fast_timeout)
    assert await runner._handle_message(_make_event()) == "agent-response"
