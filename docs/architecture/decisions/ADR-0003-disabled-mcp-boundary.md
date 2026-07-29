# ADR-0003: Disabled MCP Boundary Before Read-Only Connectors

Status: accepted

Date: 2026-07-29

## Decision

Hermes includes an MCP-ready boundary but keeps it disabled until the
read-only connector milestone explicitly authorises provider integration.

## Rationale

The project needs a clean contract for future Gmail, Calendar and ClickUp
context without accidentally enabling live external access.

## Consequences

MCP resource collection fails closed today. Tool schemas are classified as
read, write or unknown before any future provider may use them.
