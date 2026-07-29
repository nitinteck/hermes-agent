# ADR-0018: Skills are selected, not executed

Date: 2026-07-29

Status: Accepted

Decision: Executive Reasoning may select skill labels for the response plan,
but v1 must not execute skills, invoke adapters or dispatch tools.

Consequence: skill selection is safe prompt and trace metadata only. It can be
used to guide the LLM response style while preserving
`execution_boundary=not_executed`.
