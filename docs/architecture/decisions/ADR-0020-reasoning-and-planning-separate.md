# ADR-0020: Reasoning and Planning Stay Separate

Decision: Executive Reasoning decides thinking mode, evidence needs and
response shape. Executive Planning creates candidate plans only after a safe
planning ReasoningPlan exists.

Reason: keeping the layers separate prevents prompt-only planning from
silently becoming approval or execution logic.
