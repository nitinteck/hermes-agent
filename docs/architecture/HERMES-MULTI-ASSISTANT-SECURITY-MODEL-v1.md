# Hermes Multi-Assistant Security Model v1

Last updated: 2026-07-30

## Purpose

Hermes can power internal and customer-facing assistants for the same tenant.
Security separation is mandatory. A public assistant must not inherit Donna's
identity, internal knowledge, executive context or permissions.

## Binding Requirements

1. Tenant isolation: no assistant may read data belonging to another tenant.
2. Assistant-instance isolation: a public assistant may not access internal
   Donna context merely because both assistants belong to the same tenant.
3. Audience-based disclosure: knowledge availability does not imply disclosure
   permission.
4. Number-based routing: the inbound WhatsApp number identifies the endpoint,
   but participant identity and audience must still be resolved independently.
5. Unknown-contact policy: unknown contacts default to the least privileged
   public policy.
6. Internal access: internal users must be explicitly authorised; address-book
   presence is not proof of privileged access.
7. Cross-assistant access: future sharing must be explicit, audited and policy
   governed.
8. Conversation isolation: a parent conversation must not influence another
   parent's context unless converted into approved, non-personal organisational
   knowledge.
9. Personal data: customer information must be minimised, purpose limited and
   retained according to policy.
10. Auditability: routing, policy, escalation and disclosure decisions must be
    auditable.
11. Execution receipts: no assistant may claim an action was completed without
    an approved execution receipt.
12. Channel safety: public outputs must not reveal internal prompts, raw
    Executive Context, confidential Business Knowledge or diagnostic details.

## Internal Assistant Boundary

Donna by Hermes is internal. Donna may answer from approved internal context
only for authorised internal participants and only within the active capability
truth boundary.

Donna is context-aware, anticipatory, commercially intelligent, concise,
discreet, willing to challenge assumptions, honest about uncertainty, able to
preserve active decision frames, prohibited from fabricating completed actions
and proactive only within explicit authority.

## Public Assistant Boundary

The Parent Assistant or approved customer-facing brand identity is public. It
may answer only from approved public programme, venue, pricing, policy and
FAQ knowledge. It must escalate rather than improvise for safeguarding,
complaints, medical, legal, payment and data-protection topics.

The Parent Assistant must not access:

- confidential Executive Context;
- internal strategy;
- financial performance;
- legal matters;
- HR matters;
- private staff conversations;
- internal decision logs;
- restricted Business Knowledge;
- other customers' data.

## Enforcement Principle

Prompting is not a security boundary. Repositories, disclosure policy,
participant identity, assistant-instance policy and audit controls must enforce
the boundary before reasoning receives context.
