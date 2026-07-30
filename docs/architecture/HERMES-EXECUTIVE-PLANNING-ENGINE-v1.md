# Hermes Executive Planning Engine v1

Last updated: 2026-07-30

## Position

Executive Reasoning decides what kind of thinking is needed. Executive
Planning turns an eligible `ReasoningPlan` into deterministic candidate plans.
The 2026-07-30 hardening branch expands the canonical contracts and validation
surface without adding Approval, Execution or any external connector capability.

Runtime flow:

```text
User Request -> Executive Orchestrator -> Executive Context -> Executive Intelligence
-> Executive Reasoning -> ReasoningPlan -> Planning Eligibility Check
-> Executive Planning -> Candidate Plans -> Deterministic Evaluation
-> Recommended Proposed Plan -> ResponsePlan/Prompt -> AIAgent -> STOP
```

The Planning Engine is deterministic, request-scoped and proposal-only. It does
not call integrations, load credentials, execute skills, invoke MCP, call
subprocesses, send messages, write external records, approve plans or authorise
execution.

## Terms

Objective: the outcome the user or organisation seeks.
Constraint: a mandatory boundary the plan must respect.
Assumption: a proposition treated as true for planning but not verified.
Dependency: a prerequisite relationship between plan elements.
Workstream: a coherent group of related activities.
Milestone: a measurable intermediate result.
Plan Step: a bounded unit of planned work.
Decision Point: a point where a choice or authorisation is required.
Risk: a condition that could impair success.
Mitigation: a proposed measure to reduce a risk.
Success Measure: a measurable indicator of plan progress or completion.
Candidate Plan: a possible route for achieving the objective.
Recommended Plan: the preferred candidate and rationale.
Proposed Action: a descriptive reference to possible future action.
Approval Requirement: the future human approval needed before action.
Execution Receipt: future proof that authorised execution occurred.

## Contracts

Canonical v1 contracts live in:

- `gateway/executive_planning.py`

Important objects:

- `ExecutivePlanningRequest`
- `ExecutivePlan`
- `CandidatePlan`
- `PlanObjective`
- `PlanConstraint`
- `PlanAssumption`
- `PlanWorkstream`
- `PlanMilestone`
- `PlanStep`
- `PlanDependency`
- `PlanDecisionPoint`
- `PlanRisk`
- `PlanMitigation`
- `PlanSuccessMeasure`
- `ApprovalRequirement`
- `ProposedActionReference`
- `PlanEvaluation`
- `PlanRecommendation`
- `PlanningSnapshot`
- `PlanningError`
- `PlanningExecutionResult`

Mandatory v1 terminal state:

```text
plan_status=proposed
approval_status=not_requested
execution_status=not_executed
```

The dataclasses reject executable, approved, authorised, executing, executed or
completed terminal states. Proposed action references cannot bind adapter IDs
or carry external payloads.

`ExecutivePlan` carries tenant/user/request/reasoning identifiers, objective
decomposition, scope, constraints, assumptions, workstreams, milestones, steps,
dependencies, decision points, risks, mitigations, success measures, resource
requirements, owner requirements, evidence references, transparent evaluation,
recommendation, confidence, sensitivity, lifecycle state and safe trace
metadata. `CandidatePlan` is a concrete `ExecutivePlan` subclass with candidate
name, time horizon, resource profile, complexity, reversibility and evidence
coverage.

`ApprovalRequirement` is a contract only. Its v1 status and approval status are
always `not_requested`. `ProposedActionReference` is descriptive only. It may
name a future capability or external system, but it cannot contain credentials,
adapter bindings, live payloads, command text or execution receipts.

## Eligibility

Planning runs only when all conditions are true:

- Planning Engine is enabled.
- Request classification is `planning_request`.
- Reasoning mode is `planning_stub`.
- Reasoning plan does not permit execution.
- A non-empty objective is available.
- The ReasoningPlan remains non-executing and uses `planning_stub`.

Simple questions, unsupported requests and requests lacking an objective bypass
planning or fail closed. Shell/subprocess-like payloads fail closed.
External-action language may be represented only as descriptive proposed-action
references after Reasoning has already produced an eligible non-executing
planning stub; the gateway still blocks direct execution requests before model
invocation.

## Strategies

Initial deterministic strategies:

- `milestone_plan`
- `implementation_plan`
- `decision_plan`
- `review_plan`

Strategies are not Skills. Strategy selection may consume safe Skill metadata
from Reasoning, such as `milestone_planning`, but skills are never executed.

## Evaluation

Candidate evaluation is deterministic and transparent. Criteria include
evidence fit, safety boundary and sequence clarity. The formula is
`sum(rating * weight)`. Scores are safe trace metadata, not hidden model
judgments. The recommendation names tradeoffs, alternate conditions,
unresolved assumptions and the approval boundary.

## Safety

The Planning Engine cannot create tasks, calendar events, emails, WhatsApp
messages, Slack messages, CRM records, webhooks, MCP calls, subprocesses or
shell commands. External systems remain unavailable.

Plans are supplied to the reasoning provider as labelled context under
`EXECUTIVE PLANNING SNAPSHOT`. The provider may present the plan; it cannot
turn the plan into approval or execution.

## Storage

Planning v1 is request-scoped. Full plan bodies are not durably persisted by
Hermes. Operator traces may contain safe digests, counts, lifecycle state,
approval state, execution state, selected strategy, error codes and validation
results, but not raw private plan text, credentials, prompts or external
payloads.
