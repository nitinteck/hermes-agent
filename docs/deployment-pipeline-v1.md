# Hermes Deployment Pipeline v1

`hermes deploy` is the permanent deployment gate for OVOS milestones on the
Hermes VPS.

## Current Architecture

- VPS SSH alias: `hermes-vps`.
- Runtime service: user-scoped `hermes-gateway.service`.
- Gateway process:
  `/opt/ai-stack/hermes-agent/venv/bin/python -m hermes_cli.main gateway run`.
- Hermes Agent checkout: `/opt/ai-stack/hermes-agent`.
- OVOS Core checkout: `/opt/ai-stack/ovos-core`.
- OVOS is installed editable into the Hermes Agent virtual environment.
- OVOS production credentials are injected through
  `/opt/ai-stack/ovos-core/.env.supabase` via the systemd drop-in
  `hermes-gateway.service.d/ovos.conf`.
- Existing local database validation uses Supabase CLI against local ports only.
- Production migrations are applied with `npx supabase db push` from the OVOS
  checkout after a dry run.

The gateway API server is intentionally disabled unless explicitly configured,
so deployment health uses systemd, gateway runtime state, OVOS status, Supabase
migration state and EDE CLI smoke tests instead of assuming an HTTP API port.

## Command

Dry-run plan:

```bash
hermes deploy
```

Execute:

```bash
hermes deploy --execute --expected-ovos-commit <sha>
```

## Fail-Closed Order

1. Resolve and verify the expected OVOS `origin/main` commit.
2. Run local validation unless `--skip-local-validation` is explicitly used:
   compileall, pytest, ruff, format check, mypy, local Supabase reset and all
   EDE/Hermes MVP pgtap suites.
3. Verify local `main == origin/main`.
4. Verify remote tracked files are clean.
5. Run production migration dry-run.
6. Pull/reset remote OVOS to `origin/main`.
7. Verify the editable OVOS install in the Hermes venv, reinstalling only if
   the active import path is not the deployed OVOS checkout.
8. Apply production migrations.
9. Restart only `hermes-gateway.service`.
10. Wait for active service state.
11. Run health verification.
12. Run smoke tests.
13. Emit a JSON deployment report.

If any step fails, later steps do not run.

## Health Verification

The health gate checks:

- Hermes gateway systemd service is active.
- A `hermes_cli.main gateway run` process exists.
- Required OVOS Supabase environment variables are present without printing
  secret values.
- Production Supabase migrations include the Hermes MVP migration
  `20260729130000`.
- `/ovos status --json` reports a non-critical state and a running gateway.
- The deployed OVOS commit matches the expected SHA.

## Smoke Tests

The smoke gate checks:

- `hermes --version` starts.
- EDE Event Journal fixture ingestion works locally on the VPS.
- EDE Event Journal list works.
- deterministic Daily Brief generation works.
- EDE-007A execution targets still report `live adapter: none`.
- EDE-007A controls still expose the Execution Safety Kernel.

No live execution adapter is enabled by this pipeline.
