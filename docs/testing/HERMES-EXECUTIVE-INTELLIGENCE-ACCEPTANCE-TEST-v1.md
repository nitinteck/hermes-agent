# Hermes Executive Intelligence Acceptance Test v1

Last updated: 2026-07-29

Synthetic scenario:

- three meetings
- one conflict
- one long focus block
- one back-to-back sequence
- one strategic external meeting lacking preparation
- one commitment due today
- one overdue commitment
- one unavailable provider

Expected intelligence:

- `meeting_count`
- `scheduled_duration`
- `next_meeting`
- `meeting_conflict`
- `longest_focus_block`
- `meeting_load`
- `preparation_gap`
- `commitment_due`
- `commitment_overdue`
- `required_context_unavailable`

The pack uses no private production data and no live connector.

Validation command:

```bash
python -m pytest tests/gateway/test_executive_intelligence.py tests/hermes_cli/test_executive_intelligence_cli.py -q
```
