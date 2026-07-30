# Hermes Licensing Model v1

Last updated: 2026-07-30

## Commercial Unit

The initial commercial unit is one licensed assistant number per month.

One active assistant licence permits one active licensed assistant number unless
the commercial plan explicitly provides otherwise.

## Rules

1. One monthly subscription entitlement corresponds to one licensed assistant
   number.
2. A tenant may have multiple licensed assistant numbers.
3. Each assistant number may have a different role, audience, knowledge scope,
   permissions, persona, escalation policy, business hours and language.
4. Internal and public assistants are separately licensed and separately
   configured.
5. Subscription status must eventually influence activation: trial, active,
   grace, suspended and cancelled.
6. Billing failure must not immediately destroy customer data.
7. Suspension disables active service while preserving governed records
   according to policy.
8. Usage-based charges may be introduced later, but are outside v1.
9. Future channels must not silently create additional commercial entitlement.
10. Pricing is a commercial decision and must not be hard-coded into core
    architecture.

## Non-Goals

This document does not define a billing engine, payment collection,
invoicing, tax treatment, usage metering implementation or runtime entitlement
enforcement.
