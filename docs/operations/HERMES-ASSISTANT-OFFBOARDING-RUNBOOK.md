# Hermes Assistant Offboarding Runbook

Last updated: 2026-07-30

## Purpose

Offboarding safely suspends, cancels or closes a licensed assistant instance
while preserving required audit records and applying retention policy.

## Steps

1. Confirm offboarding authority.
2. Identify tenant, subscription, assistant licence and assistant instance.
3. Suspend assistant service.
4. Stop inbound or outbound behaviour as required.
5. Preserve required audit records.
6. Revoke credentials.
7. Disconnect number.
8. Revoke staff access.
9. Export approved customer data where contractually required.
10. Apply retention and deletion policy.
11. Resolve open conversations.
12. Confirm final billing.
13. Mark licence cancelled.
14. Close tenant only when no active licences or obligations remain.

## Rules

- A cancelled licence must not remain operational.
- Billing failure must not immediately destroy customer data.
- Suspended service should preserve governed records according to policy.
- Secrets must be revoked through secret-management procedures, not ordinary
  product records.
