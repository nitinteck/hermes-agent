# ADR-0023: Planning Cannot Call Integrations Directly

Decision: Planning strategies cannot call Gmail, Calendar, ClickUp, Slack,
WhatsApp, CRM, MCP, webhooks, subprocesses, shell commands or adapters.

Reason: Planning must remain deterministic and non-mutating.
