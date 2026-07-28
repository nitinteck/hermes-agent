"""Tests for the authorized_gateway_dispatch plugin hook."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent, MessageType
from gateway.session import SessionSource


def _make_event(text: str = "hello") -> MessageEvent:
    return MessageEvent(
        text=text,
        message_type=MessageType.DOCUMENT,
        message_id="message-1",
        media_urls=["/tmp/document.pdf"],
        media_types=["application/pdf"],
        raw_message={
            "fileName": "document.pdf",
            "timestamp": 123,
            "whatsapp_forwarded": True,
        },
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
    runner._scale_to_zero_note_real_inbound = MagicMock()
    return runner


@pytest.mark.asyncio
async def test_hook_runs_after_authorization_with_complete_event(monkeypatch):
    event = _make_event()
    seen = {}

    def _hook(name, **kwargs):
        assert name == "authorized_gateway_dispatch"
        seen["event"] = kwargs["event"]
        seen["gateway"] = kwargs["gateway"]
        seen["session_store"] = kwargs["session_store"]
        return [{"action": "respond", "text": "natural response"}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _hook)
    runner = _make_runner()

    result = await runner._handle_message(event)

    runner._is_user_authorized.assert_called_once_with(event.source)
    assert seen["event"] is event
    assert seen["event"].media_urls == ["/tmp/document.pdf"]
    assert seen["event"].raw_message["fileName"] == "document.pdf"
    assert seen["event"].raw_message["whatsapp_forwarded"] is True
    assert seen["event"].message_id == "message-1"
    assert seen["event"].reply_to_message_id == "quoted-1"
    assert seen["event"].reply_to_text == "quoted text"
    assert seen["gateway"] is runner
    assert seen["session_store"] is runner.session_store
    assert result == "natural response"
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_hook_does_not_run_for_unauthorized_sender(monkeypatch):
    seen_hook_names = []

    def sync_hook(name, **kwargs):
        seen_hook_names.append(name)
        return [{"action": "respond", "text": "unsafe"}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", sync_hook)
    runner = _make_runner()
    runner._is_user_authorized.return_value = False
    runner._get_unauthorized_dm_behavior = MagicMock(return_value="ignore")

    result = await runner._handle_message(_make_event())

    assert result is None
    assert "pre_gateway_dispatch" in seen_hook_names
    assert "authorized_gateway_dispatch" not in seen_hook_names


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["skip", "respond"])
async def test_terminal_actions_stop_dispatch(monkeypatch, action):
    payload = {"action": action, "text": "handled", "reason": "handled"}

    def _hook(*args, **kwargs):
        return [payload, {"action": "rewrite", "text": "must-not-win"}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _hook)
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert result == ("handled" if action == "respond" else None)
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorized_hook_response_is_sanitized_before_visible_dispatch(
    monkeypatch,
):
    def _hook(*args, **kwargs):
        return [{"action": "respond", "text": "Saved: My favourite colour is green."}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _hook)
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert result == "Got it. I'll remember My favourite colour is green."
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorized_hook_duplicate_saved_response_is_sanitized(monkeypatch):
    def _hook(*args, **kwargs):
        return [{"action": "respond", "text": "Already saved: Project note."}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _hook)
    runner = _make_runner()

    result = await runner._handle_message(_make_event())

    assert result == "Got it. I'll remember Project note."
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        '{"event_type":"capture.saved","id":"CAP-1"}',
        '{"capture_id":"CAP-20260721-0001","title":"Internal"}',
        "Traceback (most recent call last):\nRuntimeError: database unavailable",
    ],
)
async def test_authorized_hook_internal_payload_fails_open_to_normal_dispatch(
    monkeypatch,
    payload,
):
    def _hook(*args, **kwargs):
        return [{"action": "respond", "text": payload}]

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _hook)
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

    def _hook(*args, **kwargs):
        return next(results)

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _hook)
    runner = _make_runner()

    await runner._handle_message(_make_event("original"))
    assert runner._handle_message_with_agent.await_args.args[0].text == "rewritten"

    runner._handle_message_with_agent.reset_mock()
    await runner._handle_message(_make_event("original"))
    assert runner._handle_message_with_agent.await_args.args[0].text == "original"


@pytest.mark.asyncio
async def test_exception_fails_open(monkeypatch):
    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", lambda *args, **kwargs: [])
    runner = _make_runner()

    def _raising(*args, **kwargs):
        raise RuntimeError("contained")

    monkeypatch.setattr("hermes_cli.plugins.invoke_hook", _raising)
    assert await runner._handle_message(_make_event()) == "agent-response"
