# EDE-004 Organisational Knowledge Graph Shadow Boundary

Hermes does not own the Organisational Knowledge Graph.

Hermes may pass authorised, tenant-scoped conversation events to OVOS shadow hooks. OVOS may interpret those events, generate advisory reasoning and project reviewed knowledge into its persistent OKG.

Hermes boundaries:

- no user-visible response changes from OKG projection;
- no OKG projection acknowledgement in WhatsApp;
- no external action execution;
- no pattern activation;
- no direct graph mutation in Hermes gateway code;
- no graph IDs, evidence IDs or internal traversal details in normal replies.

The normal Hermes response path remains authoritative for user-visible output.

