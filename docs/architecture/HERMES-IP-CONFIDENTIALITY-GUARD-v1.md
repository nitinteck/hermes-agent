# Hermes IP Confidentiality Guard v1

Last updated: 2026-07-30

## Purpose

The IP Confidentiality Guard prevents normal user-channel responses from
exposing proprietary Hermes implementation detail. WhatsApp and WhatsApp Cloud
default to `user_safe` output.

## Disclosure Classes

- `public_safe`: safe for public documentation.
- `user_safe`: safe for ordinary owner/user chat.
- `internal`: available only inside reasoning and trace metadata.
- `restricted_operator`: safe only for a separately authenticated operator mode.

## Protected Concepts

Normal WhatsApp output must not disclose repository names, file paths, class or
method names, prompts, routing internals, provider-selection internals, feature
flag names, trace identifiers, service names, PIDs, commits, migrations,
database schema detail, deployment procedure detail, or internal safety-control
implementation.

The safe summary is:

`Hermes gathers relevant information, analyses priorities, supports decisions, and prepares proposed plans.`

## Runtime Flow

Draft response -> IP disclosure scan -> capability-truth validation ->
safety-state validation -> secret scan -> sanitization or fail-closed fallback
-> user-channel delivery.

Operator diagnostics expose safe counts and digests only.
