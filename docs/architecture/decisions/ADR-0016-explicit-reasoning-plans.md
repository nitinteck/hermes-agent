# ADR-0016: Explicit reasoning plans precede provider calls

Date: 2026-07-29

Status: Accepted

Decision: Hermes creates a deterministic `ReasoningPlan` and `ResponsePlan`
before the configured reasoning provider receives a normal turn.

Consequence: the LLM receives an explicit strategy, evidence plan, confidence
labels and limitations selected by Hermes. The plans are traceable and
redacted, and they do not authorise execution.
