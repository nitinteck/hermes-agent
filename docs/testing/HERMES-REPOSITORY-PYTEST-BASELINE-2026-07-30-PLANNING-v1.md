# Hermes Repository Pytest Baseline - Planning v1 Hardening

Date: 2026-07-30

Branch: `codex/hermes-executive-planning-engine-v1-hardening`

Base commit before hardening changes:
`a0494e5864498aca3520eb2508bf3955837a1913`

## Purpose

This artifact tracks the repository-wide test baseline separately from the
focused Planning Engine v1 gates. It prevents this milestone from claiming
unrelated repository health and keeps planning defects distinct from existing
suite debt.

## Production-Critical Focused Gates

Required touched-area gates:

```bash
.venv/bin/python -m pytest tests/gateway/test_executive_planning.py tests/hermes_cli/test_executive_planning_cli.py -q
.venv/bin/python -m ruff check gateway/executive_planning.py tests/gateway/test_executive_planning.py tests/hermes_cli/test_executive_planning_cli.py
```

Broader integration gates to attempt before PR review:

```bash
.venv/bin/python -m pytest tests/gateway/test_executive_reasoning.py tests/gateway/test_executive_orchestrator.py tests/hermes_cli/test_executive_reasoning_cli.py tests/hermes_cli/test_executive_orchestrator_cli.py -q
.venv/bin/python -m compileall gateway hermes_cli
.venv/bin/python -m ruff check gateway/executive_planning.py gateway/executive_orchestrator.py hermes_cli/executive_planning.py tests/gateway/test_executive_planning.py tests/hermes_cli/test_executive_planning_cli.py
git diff --check
```

## Repository-Wide Baseline Rule

Attempt the full repository suite when practical, but do not fix unrelated
failures in this milestone and do not report the full suite as passing unless
it completes successfully.

Record for the full attempt:

- commit SHA under test;
- approximate collected test count;
- point of interruption if stopped;
- failure categories;
- whether failures touch Planning Engine files;
- any known logging-fixture or environment issues.

## Known Baseline Limitations

- 2026-07-30 full-suite attempt:
  `.venv/bin/python -m pytest -q --maxfail=20`
- Result at cutoff:
  `18 failed, 749 passed, 2 skipped, 66 deselected, 2 errors`.
- Point of interruption:
  stopped by `--maxfail=20`.
- Observed failure categories:
  ACP edit-approval tests treated sandbox `/private/.../T` paths as sensitive;
  LSP tests hit the live-system `os.kill` guard on subprocess shutdown;
  sidecar wire-invariant tests could not bind localhost sockets in the sandbox;
  sidecar flush tests attempted to write logs under `/Users/.../.hermes/logs`;
  Anthropic OAuth setup tests intersected credential/environment behaviour.
- Planning impact:
  no failures were in `gateway/executive_planning.py`,
  `hermes_cli/executive_planning.py`, or focused Planning tests.

- Historical repository-wide formatting and environment debt is tracked in
  `docs/HERMES-TEST-BASELINE.md`.
- macOS local `python3` may be too old for the project; use `.venv/bin/python`.
- Connector and deployment tests may require environment setup that this
  proposal-only milestone must not alter.

## Milestone Invariant

Planning Engine v1 hardening must add no focused-suite failures in touched
areas. Approval, execution, external adapters, MCP, subprocesses and connector
mutations remain outside the Planning Engine.
