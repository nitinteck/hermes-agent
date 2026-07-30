# Hermes Licensed Assistant Domain v1

Last updated: 2026-07-30

## Domain Purpose

The licensed assistant domain models the commercial and operational units used
to provide Hermes-powered assistants to customer organisations.

## Core Concepts

### Tenant

A tenant represents a customer organisation.

Required characteristics:

- unique tenant identity;
- subscription status;
- data residency or region where relevant;
- billing owner;
- onboarding status;
- governance configuration;
- default escalation contact;
- audit scope.

### Subscription

A subscription represents the commercial relationship. It is not a billing
engine.

Suggested attributes:

- tenant_id;
- subscription plan;
- status;
- start date;
- renewal date;
- billing cycle;
- licensed assistant quantity;
- usage limits where applicable;
- grace or suspension state;
- commercial metadata reference;
- created_at;
- updated_at.

### Assistant Licence

An assistant licence represents one monthly licensed assistant entitlement.

Suggested attributes:

- tenant_id;
- subscription_id;
- licence status;
- assigned assistant instance;
- primary channel type;
- primary WhatsApp number reference;
- activation date;
- renewal date;
- suspension date;
- cancellation date;
- plan or capability tier.

Commercial rule: one active assistant licence permits one active licensed
assistant number unless the commercial plan explicitly provides otherwise.

### Assistant Instance

An assistant instance represents the configured AI employee.

Suggested attributes:

- tenant_id;
- assistant name;
- role;
- purpose;
- audience type;
- persona profile;
- knowledge scope;
- disclosure policy;
- capability policy;
- escalation policy;
- business hours;
- language and tone;
- status;
- onboarding version;
- configuration version.

### Channel Endpoint

A channel endpoint represents the communication endpoint. The initial channel
is WhatsApp.

Suggested attributes:

- tenant_id;
- assistant_instance_id;
- channel type;
- phone number reference;
- provider reference;
- connection status;
- inbound enabled;
- outbound enabled;
- owner-only, internal or public classification;
- verification status;
- health status;
- last health check;
- activated_at;
- suspended_at.

Provider credentials, tokens and secrets must not be stored in ordinary product
records or documentation.

### Audience And Participant

Audience classifications include:

- owner;
- internal leadership;
- internal employee;
- parent;
- prospective parent;
- school contact;
- franchise prospect;
- supplier;
- external partner;
- unknown public contact.

Participant identity must be resolved before privileged context is loaded.
Unknown public users receive the lowest-permission customer-facing policy.

### Knowledge Scope

Every assistant instance has an explicit knowledge boundary.

Donna may use approved Executive Context, internal Business Knowledge, current
decisions, projects, risks, internal policies and authorised operational
knowledge.

Parent Assistant may use approved programme facts, public schedules, approved
prices, approved FAQs, venue information, safeguarding guidance, booking
instructions and approved customer policies.

Knowledge scope must be enforced by repositories and disclosure policies, not
solely by prompting.

### Capability Scope

Assistant instances have separate effective capabilities, such as answer,
draft, summarise, classify enquiry, recommend, collect contact details,
escalate, read approved data, and future approved actions.

RC1 baseline:

- no live execution;
- no email sending;
- no calendar changes;
- no ClickUp changes;
- no external connector execution;
- no autonomous self-modification.

### Escalation Policy

Each assistant defines escalation recipient, channel, category, urgency,
business hours, expected response time, included information, excluded
information and fallback.

Parent escalation categories include safeguarding concern, complaint, refund
dispute, payment issue, medical or allergy information, legal threat,
data-protection request, unusual request and assistant uncertainty.

## Onboarding Status Model

Reusable status values:

- qualification;
- contracted;
- tenant_created;
- licence_allocated;
- assistant_defined;
- number_provisioned;
- knowledge_pending;
- knowledge_review;
- configured;
- testing;
- customer_acceptance;
- soft_launch;
- live;
- suspended;
- offboarding;
- closed.

This status model is architectural only. It is not implemented in production
code or migrations by this task.
