# ADR-0010: Facts, signals, inferences and recommendations remain distinct

Date: 2026-07-29

Status: Accepted

Decision: signals must declare `fact_or_inference` as `source_fact`,
`derived_fact`, `deterministic_signal` or `inference`.

Consequence: v1 deterministic modules cannot label broad inference as fact, and
recommendations remain outside the intelligence engine.
