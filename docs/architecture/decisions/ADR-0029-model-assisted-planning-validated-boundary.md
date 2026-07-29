# ADR-0029: Model-Assisted Planning Must Stay Inside Validated Contracts

Decision: model-assisted planning is disabled for v1. If later enabled, model
output must be validated into deterministic planning contracts before use.

Reason: the model cannot control eligibility, state transitions, approvals,
dependencies or execution status.
