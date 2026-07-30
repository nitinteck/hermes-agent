# Hermes Internal vs Public Assistant Boundary

Last updated: 2026-07-30

## Purpose

This security note defines the boundary between Donna by Hermes and
customer-facing assistants such as Parent Assistant.

## Donna Boundary

Donna is internal. Donna may use approved Executive Context and internal
Business Knowledge only for authorised internal users.

Donna must not disclose internal strategy, private staff conversations,
financial performance, legal matters, HR matters, restricted Business
Knowledge, internal decision logs or diagnostic details to public users.

## Parent Assistant Boundary

Parent Assistant is public. It may use approved programme, age, venue,
schedule, pricing, FAQ, safeguarding, booking and policy knowledge.

It must not access confidential Executive Context, internal strategy,
financial performance, legal matters, HR matters, private staff conversations,
internal decision logs, restricted Business Knowledge or other customers' data.

## Enforcement

The boundary must be enforced before reasoning:

- tenant isolation;
- assistant-instance isolation;
- participant identity resolution;
- audience-based disclosure;
- repository-level knowledge scope;
- explicit capability scope;
- escalation policy;
- audit records.

Prompt text alone is not an enforcement boundary.

## Truthfulness Rule

No assistant may claim that an action, booking, payment, email, task,
escalation or external mutation occurred without a verified execution receipt.
