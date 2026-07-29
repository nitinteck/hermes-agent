# Hermes Test Baseline

Last updated: 2026-07-29T16:14:31Z

This baseline distinguishes changed-code validation from known repository-wide
debt. It must not be read as a claim that skipped or blocked checks passed.

## Passing Focused Checks

- `tests/hermes_cli/test_deployment_pipeline.py`
- `tests/hermes_cli/test_executive_orchestrator_cli.py`
- `tests/gateway/test_executive_orchestrator.py`
- `tests/gateway/test_readiness.py`

These cover:

- portable fail-closed deploy path resolution
- no Mac OVOS default selected on VPS-like layouts
- clear deploy failure when local OVOS path is unavailable
- local-only diagnostic Orchestrator path
- redacted trace lookup
- request classification
- fail-closed potentially executable requests
- `execution_state=not_executed`
- enabled/disabled Orchestrator behaviour

## Known Baseline Debt

- The local system `python3` is Python 3.9 and fails on repository type syntax.
  Use `.venv/bin/python`.
- Repo-wide `ruff format --check .` has substantial pre-existing debt and must
  be treated separately from touched-file formatting.
- Targeted `mypy` over changed Orchestrator/deployment modules reaches
  pre-existing transitive import/type debt, including missing optional stubs and
  unrelated legacy syntax. This is not a new Orchestrator regression.
- A full `scripts/run_tests.sh -q` baseline run was interrupted at roughly
  79.9 percent after more than 35,000 passing tests and 22 observed failures.
  Observed failures were platform/environment-sensitive or unrelated baseline
  tests. The one adjacent CLI startup-registry failure was fixed in this branch.

## Observed Full-Suite Failures

- credential profile isolation: local profile state leaked into a test that
  expects no profile `auth.json`.
- Anthropic OAuth setup token tests: mocked token JSON shape no longer matched
  the expected decoder input.
- gateway background media routing: `/tmp` versus `/private/tmp` path mismatch
  on macOS.
- detailed health endpoint: local environment returned `degraded` rather than
  `ok`.
- shutdown/systemd/gateway-service tests: local macOS environment lacks Linux
  systemd semantics or expected process behaviour.
- CLI startup built-in registry parity: fixed here by registering `deploy`,
  `executive-orchestrator` and `eo` as built-in top-level commands.
- live system guard self-test: local macOS environment does not provide
  `systemctl`.

## Production-Critical Failures

None identified in the focused changed-code validation. Any future failure in
gateway startup, WhatsApp bridge, Orchestrator enablement, Safety Kernel
non-execution or Supabase migration reachability is production-critical and
must be fixed before declaring readiness.

## Required Reproduction

Use the repo venv:

```bash
.venv/bin/python -m pytest tests/hermes_cli/test_deployment_pipeline.py -q
.venv/bin/python -m pytest tests/hermes_cli/test_executive_orchestrator_cli.py tests/gateway/test_executive_orchestrator.py tests/gateway/test_readiness.py -q
.venv/bin/python -m pytest tests/hermes_cli/test_startup_plugin_gating.py::test_builtin_set_covers_every_registered_subcommand -q
.venv/bin/python -m ruff check hermes_cli/deployment.py hermes_cli/subcommands/deploy.py hermes_cli/executive_orchestrator.py hermes_cli/main.py gateway/executive_orchestrator.py tests/hermes_cli/test_deployment_pipeline.py tests/hermes_cli/test_executive_orchestrator_cli.py
.venv/bin/python -m ruff format --check hermes_cli/deployment.py hermes_cli/subcommands/deploy.py hermes_cli/executive_orchestrator.py gateway/executive_orchestrator.py tests/hermes_cli/test_deployment_pipeline.py tests/hermes_cli/test_executive_orchestrator_cli.py
.venv/bin/python -m mypy hermes_cli/deployment.py hermes_cli/executive_orchestrator.py gateway/executive_orchestrator.py
git diff --check
```
