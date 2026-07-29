# ADR-0009: Every intelligence signal requires evidence

Date: 2026-07-29

Status: Accepted

Decision: every `ExecutiveIntelligenceSignal` must include source context IDs
and `IntelligenceEvidenceReference` records.

Consequence: invalid or unsupported outputs are rejected instead of becoming
untraceable assistant claims.
