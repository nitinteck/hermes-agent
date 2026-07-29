# ADR-0007: Deterministic intelligence precedes model insight

Date: 2026-07-29

Status: Accepted

Decision: deterministic intelligence snapshots are assembled before the
reasoning provider receives the turn.

Consequence: the LLM may interpret labelled facts and signals, but it should
not be responsible for computing meeting conflicts, due dates or provider
limitations from raw context.
