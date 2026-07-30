# Hermes EDP Slice 1 Runbook

Status: operator runbook. Do not apply production migration without explicit
approval.

## Local Validation

From `ovos-core`:

```bash
python -m compileall ovos_core tests
pytest tests/test_edp_foundation_migration.py
psql "$LOCAL_DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/db/edp_foundation_slice_1_validation.sql
psql local -v ON_ERROR_STOP=1
```

For rollback-only SQL validation:

```bash
(printf 'begin;\n'; cat supabase/migrations/20260730120000_edp_foundation_slice_1.sql; printf '\nrollback;\n') | psql local -v ON_ERROR_STOP=1 -q
```

From `hermes-agent`:

```bash
python -m compileall gateway hermes_cli tests/gateway tests/hermes_cli
pytest tests/gateway/test_edp_governance.py tests/hermes_cli/test_edp_governance_cli.py
ruff check gateway/edp_governance.py hermes_cli/governance.py tests/gateway/test_edp_governance.py tests/hermes_cli/test_edp_governance_cli.py
ruff format --check gateway/edp_governance.py hermes_cli/governance.py tests/gateway/test_edp_governance.py tests/hermes_cli/test_edp_governance_cli.py
git diff --check
```

## CLI Diagnostics

```bash
hermes governance status
hermes governance capability-truth status send_email
hermes governance improvement-proposals status
```

Expected invariants:

- `external_execution=not_executed`
- `live_execution_enabled=false`
- `execution_enabled=false`
- connector enablement remains false;
- action/write capabilities remain unavailable;
- self-improvement remains proposal-only;
- secrets and tokens are not printed.

## Supabase Credentials

Preferred runtime read mode:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` or `SUPABASE_PUBLISHABLE_KEY`
- `SUPABASE_ACCESS_TOKEN`

Bounded operator diagnostics may explicitly opt in to service-role RPCs:

- `HERMES_EDP_ALLOW_SERVICE_ROLE_RPC=true`
- `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY`

Never print these values in logs, reports or CLI output.

## Production Gate

Before production migration:

1. confirm backup and restore procedure;
2. reconcile deployed `ovos-core` SHA with origin;
3. verify migration ordering;
4. run the full local database and RLS test suite;
5. confirm the migration is additive and non-destructive;
6. receive explicit deployment/migration authorisation.

Without that authorisation, stop at opened PRs.
