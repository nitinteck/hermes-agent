# Hermes Executive Planning Engine v1

Last updated: 2026-07-29

## Position

Executive Reasoning decides what kind of thinking is needed. Executive
Planning turns an eligible `ReasoningPlan` into deterministic candidate plans.

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

## Eligibility

Planning runs only when all conditions are true:

- Planning Engine is enabled.
- Request classification is `planning_request`.
- Reasoning mode is `planning_stub`.
- Reasoning plan does not permit execution.
- A non-empty objective is available.
- Any external-action language is explicitly framed as non-executing planning.

Simple questions, unsafe requests, direct external-action requests, unsupported
requests and requests lacking an objective bypass planning or fail closed.

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
evidence fit, safety boundary and sequence clarity. Scores are safe trace
metadata, not hidden model judgments. The recommendation names tradeoffs,
alternate conditions, unresolved assumptions and the approval boundary.

## Safety

The Planning Engine cannot create tasks, calendar events, emails, WhatsApp
messages, Slack messages, CRM records, webhooks, MCP calls, subprocesses or
shell commands. External systems remain unavailable.

Plans are supplied to the reasoning provider as labelled context under
`EXECUTIVE PLANNING SNAPSHOT`. The provider may present the plan; it cannot
turn the plan into approval or execution.
