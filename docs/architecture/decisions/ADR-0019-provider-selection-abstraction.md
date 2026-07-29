# ADR-0019: Provider selection is an abstraction

Date: 2026-07-29

Status: Accepted

Decision: Executive Reasoning records provider choices as abstractions such as
`standard_conversational_model`, `reasoning_model` and
`deterministic_response`.

Consequence: v1 does not instantiate model clients, load credentials or bypass
the existing AIAgent provider path. The abstraction prepares for later routing
without changing runtime execution boundaries.
