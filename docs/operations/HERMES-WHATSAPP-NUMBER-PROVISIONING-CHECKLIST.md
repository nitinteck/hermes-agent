# Hermes WhatsApp Number Provisioning Checklist

Last updated: 2026-07-30

## Purpose

Provision or connect a dedicated WhatsApp number for one licensed assistant
instance.

## Checklist

- Confirm tenant.
- Confirm subscription.
- Confirm assistant licence.
- Confirm assistant instance.
- Confirm number ownership.
- Verify provider account ownership.
- Configure provider or bridge.
- Configure inbound routing to the correct assistant instance.
- Confirm outbound policy.
- Confirm display name.
- Confirm profile information.
- Publish privacy notice.
- Confirm consent wording where required.
- Confirm owner-only, internal or public classification.
- Confirm participant identity rules.
- Confirm unknown-contact policy.
- Confirm escalation route.
- Confirm fallback route.
- Run connection health test.
- Run inbound test.
- Run response safety test.
- Confirm emergency disable process.
- Record activation date.
- Record last health check.

## Secret Boundary

Do not store provider credentials, API tokens, webhook secrets or session
material in ordinary product records, screenshots or documentation.

## RC1 Boundary

Provisioning documentation does not enable production runtime functionality.
Connectors, approvals and execution remain disabled unless a later milestone
explicitly enables them.
