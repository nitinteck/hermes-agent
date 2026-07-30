# Hermes Conversation Working Set v1

Last updated: 2026-07-30

## Purpose

The Conversation Working Set is a transient decision frame for one user,
tenant and conversation. It helps Donna keep track of active options,
criteria, assumptions and the next decision across short WhatsApp exchanges.

It is not durable Executive State and is not a canonical database.

## Scope

The v1 working set tracks:

- current topic;
- active goal;
- decision being made;
- active options;
- comparison criteria;
- confirmed facts;
- user assumptions;
- assistant inferences;
- unknowns;
- current recommendation;
- rejected options;
- user preference;
- unresolved questions;
- proposed next step;
- execution state;
- last capability boundary stated.

## Lifecycle

- Built request-time from the current message and bounded recent history.
- Bound to tenant, actor and conversation identifiers.
- Bounded to eight recent turns and short text snippets.
- Exposes a one-hour staleness check.
- Stores safe traces using digests for tenant, actor and conversation IDs.
- Does not write long-term memory.
- Does not cross conversations, users or tenants.

## Option Tracking

If the user introduces options such as:

- improve WhatsApp behaviour;
- populate Business Knowledge;
- connect Gmail;

the working set preserves those options. If the user removes the highest-risk
option, the rejected option is marked rather than silently forgotten.

## Safety Boundary

The working set can include structured summaries of recent user-visible
conversation turns. It must not store hidden prompts, raw system instructions,
credentials, unrestricted transcripts, or cross-user data.
