"""Tests for WhatsApp owner-message metadata and source-level text tagging.

The Node bridge sets ``fromOwner: true`` on inbound `fromMe` messages that
look owner-typed (linked-device send, not echoed from /send) when the
operator opts into ``WHATSAPP_FORWARD_OWNER_MESSAGES``.  These tests pin
the adapter's responsibility: lift that flag onto
``MessageEvent.metadata["whatsapp_from_owner"]``, prefix ``MessageEvent.text``
with ``[owner reply] ``, and otherwise leave metadata absent and text
unchanged.  The env-var gate itself lives in the bridge — the adapter just
trusts the payload.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.config import Platform, PlatformConfig
from plugins.platforms.whatsapp.adapter import WhatsAppAdapter


@pytest.fixture(autouse=True)
def _whatsapp_open_optin(monkeypatch):
    """Opt into WhatsApp allow-all so ``dm_policy: open`` dispatch tests run.

    The adapter fails closed on ``open`` without an allow-all opt-in
    (SECURITY.md 2.6); these owner-DM tests set ``_dm_policy = "open"``.
    """
    monkeypatch.setenv("WHATSAPP_ALLOW_ALL_USERS", "true")


def _make_adapter():
    adapter = WhatsAppAdapter.__new__(WhatsAppAdapter)
    adapter.platform = Platform.WHATSAPP
    adapter.config = PlatformConfig(enabled=True)
    adapter._message_handler = AsyncMock()
    adapter._dm_policy = "open"
    adapter._allow_from = set()
    adapter._group_policy = "open"
    adapter._group_allow_from = set()
    adapter._mention_patterns = []
    adapter._free_response_chats = set()
    adapter._whatsapp_free_response_chats = lambda: set()
    return adapter


def _dm_payload(**overrides):
    payload = {
        "messageId": "M1",
        "chatId": "6281234567890@s.whatsapp.net",
        "senderId": "6281234567890@s.whatsapp.net",
        "senderName": "Customer",
        "chatName": "Customer",
        "isGroup": False,
        "body": "hi from the linked phone",
        "hasMedia": False,
        "mediaType": "",
        "mediaUrls": [],
        "mentionedIds": [],
        "quotedParticipant": "",
        "botIds": [],
        "timestamp": 0,
    }
    payload.update(overrides)
    return payload


def test_metadata_flag_set_when_payload_has_from_owner():
    adapter = _make_adapter()
    payload = _dm_payload(fromOwner=True)

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None
    assert event.metadata.get("whatsapp_from_owner") is True
    assert event.authorized_envelope is not None
    assert event.authorized_envelope.sent_by_user is True
    assert event.text.startswith("[owner reply] ")
    assert event.text == "[owner reply] hi from the linked phone"


def test_from_owner_does_not_double_prefix_when_already_tagged():
    adapter = _make_adapter()
    payload = _dm_payload(
        fromOwner=True,
        body="[owner reply] already tagged",
    )

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None
    assert event.metadata.get("whatsapp_from_owner") is True
    assert event.text == "[owner reply] already tagged"


def test_from_owner_prefixes_empty_body_for_uniform_media_placeholders():
    """Owner media with empty caption still gets the marker (bridge may
    substitute placeholders like ``[image received]`` upstream; empty stays
    tagged for consistency)."""
    adapter = _make_adapter()
    payload = _dm_payload(fromOwner=True, body="")

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None
    assert event.metadata.get("whatsapp_from_owner") is True
    assert event.text == "[owner reply] "


def test_metadata_flag_absent_by_default():
    """Default bridge payload (env flag off → field never present) must not
    leak the metadata key.  Plugins use ``.get(...)`` and rely on absence."""
    adapter = _make_adapter()
    payload = _dm_payload()

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None
    assert "whatsapp_from_owner" not in event.metadata


def test_metadata_flag_absent_when_explicitly_false():
    """Explicit fromOwner=false must not set the metadata key — plugins
    test for truthiness, but absence is the canonical "not owner" state."""
    adapter = _make_adapter()
    payload = _dm_payload(fromOwner=False)

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None
    assert "whatsapp_from_owner" not in event.metadata


def test_authorized_envelope_preserves_truthful_whatsapp_provenance():
    adapter = _make_adapter()
    payload = _dm_payload(
        senderDisplayName="Synthetic Sender",
        senderPushName="Synthetic Sender",
        chatDisplayName="Synthetic Chat",
        fromMe=False,
        nativeType="extendedTextMessage",
        caption="Synthetic caption",
        mentionedIds=["mention@example.invalid"],
        isForwarded=True,
        forwardingScore=2,
        hasQuotedMessage=True,
        quotedMessageId="quoted-1",
        quotedRemoteJid="chat@example.invalid",
        quotedParticipant="participant@example.invalid",
        quotedText="Synthetic quoted text",
        correlationId="request-1",
        authState={"token": "must-not-escape"},
    )

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None
    envelope = event.authorized_envelope
    assert envelope is not None
    assert envelope.envelope_version == 1
    assert envelope.platform == "whatsapp"
    assert envelope.transport == "baileys"
    assert envelope.chat_id == payload["chatId"]
    assert envelope.chat_display_name == "Synthetic Chat"
    assert envelope.sender_display_name == "Synthetic Sender"
    assert envelope.sender_push_name == "Synthetic Sender"
    assert envelope.sent_by_user is False
    assert envelope.source_message_id == "M1"
    assert envelope.source_timestamp is not None
    assert envelope.caption == "Synthetic caption"
    assert envelope.mentions == ("mention@example.invalid",)
    assert envelope.is_forwarded is True
    assert envelope.forwarding_score == 2
    assert envelope.correlation_id == "request-1"
    assert envelope.quoted_message is not None
    assert envelope.quoted_message.message_id == "quoted-1"
    assert envelope.quoted_message.chat_id == "chat@example.invalid"
    assert envelope.quoted_message.sender_id == "participant@example.invalid"
    assert envelope.quoted_message.text == "Synthetic quoted text"
    assert "authState" not in envelope.as_dict()
    assert "token" not in str(envelope.as_dict())


def test_lid_is_not_claimed_as_a_verified_phone():
    adapter = _make_adapter()
    payload = _dm_payload(
        chatId="synthetic-chat@lid",
        senderId="synthetic-sender@lid",
        fromMe=False,
    )

    event = asyncio.run(adapter._build_message_event(payload))

    assert event is not None and event.authorized_envelope is not None
    assert event.authorized_envelope.sender_identifier_type == "lid"
    assert event.authorized_envelope.sender_phone is None
    assert event.authorized_envelope.sender_display_name is None
    assert event.authorized_envelope.sender_push_name is None
    assert event.authorized_envelope.chat_display_name is None
    assert event.authorized_envelope.filename is None
    assert event.authorized_envelope.caption is None


@pytest.mark.parametrize(
    ("media_type", "native_type", "mime", "native_metadata"),
    [
        ("image", "imageMessage", "image/jpeg", {}),
        ("ptt", "audioMessage", "audio/ogg", {"audio": {"ptt": True}}),
    ],
)
def test_image_and_audio_metadata_are_preserved_without_unapproved_paths(
    media_type, native_type, mime, native_metadata
):
    adapter = _make_adapter()
    payload = _dm_payload(
        hasMedia=True,
        mediaType=media_type,
        nativeType=native_type,
        mime=mime,
        fileName="synthetic.bin" if media_type == "image" else "",
        caption="Synthetic media" if media_type == "image" else "",
        nativeMetadata=native_metadata,
        mediaUrls=["/etc/passwd"],
    )

    event = asyncio.run(adapter._build_message_event(payload))
