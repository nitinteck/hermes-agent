# Hermes Product Deployment Model v1

Last updated: 2026-07-30

## Product Position

Hermes is the underlying Executive Operating System: the orchestration,
governance, identity, context, knowledge, reasoning and safety platform.

Customers subscribe to licensed AI assistant instances. In the initial product,
each licensed assistant instance is associated with a dedicated WhatsApp
number. Licensing is charged per assistant number per month.

The internal executive assistant is named Donna. Recommended presentation:
Donna by Hermes.

Donna is an internal assistant for the owner, leadership team and authorised
employees. Customer-facing assistants are separate assistant instances and must
not automatically share Donna's identity, internal knowledge, permissions or
operating configuration.

## Deployment Hierarchy

```text
Platform: Hermes
-> Tenant: customer organisation
-> Subscription: commercial entitlement
-> Assistant Licence: one billable assistant-number entitlement
-> Assistant Instance: configured AI role
-> Channel Endpoint: dedicated WhatsApp number, future channels later
-> Conversation: channel-specific interaction
```

The WhatsApp number is the first licensed deployment unit, but it is not the
permanent assistant identity. The architecture keeps assistant identity,
commercial licence and channel endpoint separate so an assistant can support
additional channels later without redesigning the domain.

## Initial Om Vidya Deployment

### Licence 1: Donna

Audience: owner, leadership and authorised internal team.

Purpose:

- executive planning;
- decision support;
- operational coordination;
- drafting;
- meeting preparation;
- internal knowledge retrieval;
- risk and priority analysis;
- controlled escalation recommendations.

Disabled in RC1:

- external execution;
- Gmail;
- Calendar;
- ClickUp;
- autonomous code changes;
- autonomous policy changes.

### Licence 2: Parent Assistant

Audience: parents, prospective parents and public enquiries.

Purpose:

- programme enquiries;
- class guidance;
- approved pricing information;
- booking guidance;
- age and programme suitability;
- FAQs;
- lead qualification;
- human escalation;
- customer-service triage.

The Parent Assistant must not go live before Business Knowledge, public
disclosure controls, assistant-instance isolation, participant identity
handling, escalation workflow and customer acceptance testing are deployed and
verified.

## Product Boundaries

This document defines product architecture only. It does not implement runtime
functionality, billing, migrations, connectors, approval recording or
execution.

RC1 remains frozen:

- no Business Knowledge migration;
- no connector enablement;
- no approvals;
- no execution;
- no deployment.
