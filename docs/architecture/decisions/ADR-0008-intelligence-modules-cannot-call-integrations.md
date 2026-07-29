# ADR-0008: Intelligence modules cannot call integrations directly

Date: 2026-07-29

Status: Accepted

Decision: intelligence modules consume `ExecutiveContextSnapshot` only.

Consequence: modules cannot load credentials, call Calendar/Gmail/ClickUp,
invoke MCP, send messages, create tasks, execute subprocesses or perform
external writes.
