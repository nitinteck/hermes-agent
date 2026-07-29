# ADR-0024: ProposedActionReference Is Non-Executable

Decision: `ProposedActionReference` is descriptive only. It cannot include an
adapter ID, credential, shell command or external payload.

Reason: future execution must pass through approval and safety boundaries
instead of hidden plan data.
