# ADR-0006: Executive Context and Executive Intelligence are separate layers

Date: 2026-07-29

Status: Accepted

Decision: Executive Context providers retrieve or observe source facts.
Executive Intelligence modules derive deterministic facts and signals from
validated context snapshots.

Consequence: context providers must not embed executive conclusions merely
because the LLM would find them useful.
