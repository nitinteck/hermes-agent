# Hermes WhatsApp Findings - 2026-07-30

## Confirmed Defects

1. Internal architecture and proprietary implementation details could appear in
   normal WhatsApp responses.
2. Internal Skill names and self-improvement events could appear in the
   WhatsApp channel.
3. Ordinary conversation appeared able to trigger profile/Skill mutation
   surfaces.
4. Execution-first sequencing could be accepted in planning.
5. Decision planning could be misclassified as execution.
6. Multi-turn Calendar-versus-Gmail context could be lost in planning.
7. Capability descriptions could drift from runtime truth.
8. Planning responses were weak on evidence, assumptions, confidence and
   proposed/not-executed status.

## Resolution

Governance hardening v1 adds user-channel IP inspection, proposal-only
self-improvement quarantine, deterministic capability truth, planning safety
repair, planning context binding, business knowledge contracts and modular
regression packs.
