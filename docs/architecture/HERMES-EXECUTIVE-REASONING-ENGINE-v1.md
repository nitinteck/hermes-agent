# Hermes Executive Reasoning Engine v1

Last updated: 2026-07-29

## Position

Executive Context answers: what labelled evidence is available?

Executive Intelligence answers: what deterministic signals can be derived?

Executive Reasoning answers: what reasoning strategy, evidence needs,
confidence labels, skill selection and response shape should be used before the
LLM sees the turn?

Runtime flow:

`Request Classification -> Executive Context -> Executive Intelligence -> Executive Reasoning Engine -> optional Executive Planning Engine -> ResponsePlan -> Context Composer -> AIAgent`

The engine is deterministic and request-scoped. It does not call integrations,
load credentials, execute skills, invoke MCP, call subprocesses, send messages,
write external records or authorise execution.

## Contracts

`ReasoningPlan` records:

- correlation ID
- request classification
- reasoning mode
- user objective
- sub-questions
- evidence needs
- missing information
- confidence labels
- selected skills
- selected provider abstraction
- safety state
- execution flags

`ResponsePlan` records:

- response goal
- evidence summary
- confidence labels
- reasoning mode
- selected skills
- selected model abstraction
- expected structure
- limitations
- safety state
- execution flags

For v1:

- `execution_required=false`
- `execution_permitted=false`
- `skill_execution=selected_not_executed`
- `external_calls_enabled=false`

## Reasoning Modes

Initial deterministic modes:

- `direct_answer`
- `executive_summary`
- `executive_brief`
- `analysis`
- `comparison`
- `planning_stub`
- `review`
- `explanation`
- `question_answering`

The mode guides response construction. It is not a workflow engine and does not
invoke tools.

## Evidence Planning

Evidence planning maps the classified request to needed source categories.

Examples:

- Meeting or schedule questions require `calendar_context` evidence. If no
  meeting evidence is selected, the plan records the limitation and instructs
  the response not to infer meetings.
- Gmail and ClickUp mentions can be advisory discussion, capability questions
  or external-action requests. The Reasoning Engine reports missing evidence;
  the Orchestrator and Safety Kernel still decide non-execution.
- News, investment portfolio and other live external data remain unavailable
  unless selected context already contains labelled evidence.

The engine never invents evidence references. It uses only references selected
by Hermes context and intelligence layers.

## Confidence Model

Claim confidence is labelled as one of:

- `known`
- `derived`
- `assumed`
- `unavailable`
- `conflicting`
- `unknown`

Assumptions must not be promoted to facts. Missing evidence is represented as
`unavailable` or `unknown` and surfaced as a limitation.

## Skill Selection

v1 may select deterministic skill labels such as:

- `milestone_planning`
- `executive_decision_support`
- `document_review`
- `policy_review`

Selected skills are not executed. Skill routing is advisory metadata for the
prompt and trace only.

## Provider Selection

v1 selects among model abstractions:

- `standard_conversational_model`
- `reasoning_model`
- `deterministic_response`

These abstractions currently map onto the existing configured provider path.
The Reasoning Engine does not instantiate model clients or load credentials.

## Operator Commands

```bash
hermes reasoning status
hermes reasoning diagnostics
hermes reasoning plans
hermes executive-orchestrator status
```

`executive-orchestrator status` exposes the Reasoning flags alongside
Orchestrator, Context and Intelligence flags.

## Runtime Flags

```bash
HERMES_EXECUTIVE_REASONING_ENGINE_ENABLED=true
HERMES_REASONING_PLANNER_ENABLED=true
HERMES_SKILL_SELECTION_ENABLED=true
HERMES_AI_PROVIDER_SELECTION_ENABLED=true
HERMES_PLANNING_ENGINE_ENABLED=true
```

Execution remains disabled:

```bash
HERMES_LIVE_EXECUTION_ENABLED=false
```

## Safety

Execution boundary: `not_executed`

Planning Engine: enabled for eligible `planning_stub` turns only

Live execution: disabled

The engine cannot enable Calendar writes, Gmail, ClickUp, Slack, CRM, MCP
execution, autonomous agents or external adapters. Planning remains a separate
proposal-only layer.
