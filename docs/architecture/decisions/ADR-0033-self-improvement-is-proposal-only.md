# ADR-0033: Self-Improvement Is Proposal-Only

Ordinary messages cannot directly mutate Skills, profile, prompts, routing or
policy. Self-improvement output becomes an `ImprovementProposal` with
`proposed`, `not_requested` and `not_applied` status.
