# Hermes Registry Model v1

Last updated: 2026-07-29

## Registries

Hermes uses domain-specific registries:

- Executive Context Provider Registry
- Intelligence Registry
- Connection Registry
- Capability Registry
- Integration Adapter Registry
- future Skill Registry

The Intelligence Registry remains separate because intelligence modules consume
canonical context and emit signals. They are not integrations, connectors,
skills, adapters, prompts or actions.

Common conventions include IDs, versions, lifecycle state, health, deterministic
status, risk and safe trace metadata.

Hermes v1 uses explicit in-process registries for integration metadata:

- `ConnectionRegistry`: supported integrations plus scoped authorised
  connections.
- `InMemoryCapabilityRegistry`: capabilities that Hermes may describe or use.
- `IntegrationAdapterRegistry`: technical adapters allowed to service
  capabilities.

These registries are intentionally small and deterministic for this milestone.
They define the contract that can later be persisted in Supabase without
changing provider semantics.

## Secret Boundary

`CredentialReference` points to a secret source. It is safe to store and trace
because it does not contain credential values.

`ResolvedCredential` contains a value only after the Credential Resolver checks
tenant/user/environment scope. It is passed only to an `IntegrationAdapter`.
Its representation and trace redact the secret.

## Governance Boundary

Context reads may call `IntegrationService.execute_read(...)`.

External writes are not executable in v1. Future action flow must remain:

`Executive Orchestrator -> Proposed Action -> Capability Registry -> Permission Check -> Approval Policy -> Safety Kernel -> IntegrationService -> IntegrationAdapter -> External System -> Execution Receipt`

Until that boundary exists and is explicitly authorised, write capabilities may
be documented but must not be invoked.
