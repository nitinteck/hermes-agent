# Hermes Business Knowledge Registry v1

Last updated: 2026-07-30

## Purpose

Business knowledge is structured as typed records, not embedded in one giant
system prompt. Availability does not imply disclosure permission.

## Record Types

Supported entity types include Group, LegalEntity, Brand, Person, Role,
Location, Programme, Product, CustomerSegment, Partner, Project, Objective,
KPI, Policy, Contract, Risk, Decision, FinancialMetric, OperatingConstraint,
Relationship and Initiative.

## Common Fields

Records include tenant, entity type, canonical name, aliases, summary, source
type/reference/authority, confidence, verification status, sensitivity,
disclosure policy, effective dates, lifecycle state, creator, supersession,
conflict group and trace metadata.

## Statuses

- `proposed`
- `verified`
- `disputed`
- `superseded`
- `expired`

## Sensitivity

- `public`
- `internal`
- `confidential`
- `restricted`
- `secret`

Restricted and secret records are not retrieved into normal WhatsApp context.
