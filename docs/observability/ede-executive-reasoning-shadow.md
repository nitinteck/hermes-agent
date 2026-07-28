# EDE Executive Reasoning Shadow Integration

Hermes exposes authorised inbound messages to OVOS through the post-authorisation `authorized_gateway_dispatch` hook.

For EDE-003, Hermes remains the channel and response authority:

- Hermes authorises the sender.
- Hermes passes the complete event, gateway and session store to authorised hooks.
- OVOS may enqueue EDE interpretation and executive reasoning as shadow work.
- Hermes continues the normal assistant response path unless an existing authorised hook explicitly returns a safe user-visible response.

EDE executive reasoning must not:

- change normal Hermes replies;
- send separate WhatsApp acknowledgements;
- expose internal reasoning or journal IDs;
- execute external actions;
- restart or alter gateway services.

The relevant regression suite is:

```bash
pytest tests/gateway/test_authorized_gateway_dispatch.py tests/hermes_cli/test_plugins.py
```

This document records the integration boundary only. The EDE reasoning engine lives in `nitinteck/ovos-core`.
