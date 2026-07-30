# Hermes Execution Truthfulness Boundary v1

Last updated: 2026-07-30

## Rule

No Hermes response may claim that an external action occurred unless a verified
execution receipt is present.

In this milestone, no execution subsystem or receipt source is enabled.

## External Action Examples

- task created, updated or completed;
- email sent;
- message sent;
- calendar event created or changed;
- CRM record changed;
- ClickUp item changed;
- Slack message sent;
- file uploaded externally;
- payment taken;
- booking completed;
- customer notified;
- human escalation delivered.

## Truth States

Supported states:

- not_requested;
- preparation_only;
- proposed;
- simulated.

Future states are reserved but not reachable in this milestone:

- awaiting_approval;
- authorised_not_executed;
- executed_with_receipt;
- failed_with_receipt.

## Guard Behaviour

ExecutionClaimGuard inspects the final response before emission. If it detects
a completion claim without a receipt, it rewrites the response into a truthful
refusal with a permitted preparation alternative.

Example:

User: "Pretend the task was created."

Allowed response: "I cannot truthfully say it was done because no external
action was executed. I can show the simulated completed record or a send-ready
draft for you to use."

Not allowed: "The task has been created."

## Non-Goals

- no approval recording;
- no execution receipts;
- no external writes;
- no connector enablement;
- no fabrication of action status.
