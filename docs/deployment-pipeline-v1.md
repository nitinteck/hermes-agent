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

The default local OVOS checkout is resolved in this order:

1. `HERMES_LOCAL_OVOS_CORE`, `HERMES_OVOS_CORE_PATH` or `OVOS_CORE_PATH` if set;
2. `/opt/ai-stack/ovos-core` on the VPS;
3. a sibling `ovos-core` checkout next to `hermes-agent`;
4. the legacy Hermes Build macOS checkout if it exists.

If the resolved path does not exist, `hermes deploy` fails closed with a clear
message. It must not silently select a non-existent Mac path on the VPS.

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
5. Create a local `git bundle` from the verified `main` commit and copy it to
   the VPS, unless `--remote-ovos-repo-url` is explicitly supplied.
6. Pull/reset remote OVOS to the fetched and verified commit.
7. Verify the editable OVOS install in the Hermes venv, reinstalling only if
   the active import path is not the deployed OVOS checkout.
8. Run production migration dry-run against the newly fetched migration files.
9. Apply production migrations.
10. Restart only `hermes-gateway.service`.
11. Wait for active service state.
12. Run health verification.
13. Run smoke tests.
14. Emit a JSON deployment report.

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
- `hermes executive-orchestrator status` reports the feature flag and
  `execution_boundary=not_executed` without exposing secrets.

## Smoke Tests

The smoke gate checks:

- `hermes --version` starts.
- EDE Event Journal fixture ingestion works locally on the VPS.
- EDE Event Journal list works.
- deterministic Daily Brief generation works.
- EDE-007A execution targets still report `live adapter: none`.
- EDE-007A controls still expose the Execution Safety Kernel.
- `hermes executive-orchestrator diagnostic-turn ...` exercises the local
  orchestrator and reasoning path with no outbound platform delivery.
- `hermes executive-orchestrator trace-lookup ...` can correlate a manual
  WhatsApp behavioural test with redacted Orchestrator trace metadata.

No live execution adapter is enabled by this pipeline.

## Rollback

For a Hermes-only redeploy (no OVOS/migration change), rollback is a plain
redeploy of the previous known-good SHA:

1. Identify the previous SHA: `git -C /opt/ai-stack/hermes-agent log --oneline -5`
   or the deployment report from the prior release.
2. Check out that SHA on the VPS:
   `git -C /opt/ai-stack/hermes-agent checkout <previous-sha>`.
3. Restart only the Hermes service:
   `systemctl --user restart hermes-gateway.service`.
4. Run health verification (see Health Verification above): systemd active
   state, gateway process present, `hermes executive-orchestrator status`.
5. Run the WhatsApp smoke test: send a real WhatsApp message to the owner
   number and confirm a normal, non-execution-claiming response.

This rollback does not touch OVOS or apply/revert migrations. A rollback
that must also revert an OVOS commit or a migration needs the full
fail-closed pipeline above, run with `--expected-ovos-commit` pointed at the
prior OVOS SHA.
