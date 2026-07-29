"""Fail-closed Hermes VPS deployment pipeline."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.code == 0


class CommandRunner(Protocol):
    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 120,
        input_text: str | None = None,
    ) -> CommandResult: ...


class SubprocessCommandRunner:
    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 120,
        input_text: str | None = None,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                code=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or f"timed out after {timeout}s",
            )
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


@dataclass(frozen=True)
class DeploymentConfig:
    remote_host: str = "hermes-vps"
    local_ovos_core: Path = Path(
        "/Users/nitinteckchandani/Projects/Hermes-Build/ovos-core"
    )
    local_ovos_python: Path | None = None
    remote_ovos_repo_url: str = "https://github.com/nitinteck/ovos-core.git"
    remote_ovos_core: str = "/opt/ai-stack/ovos-core"
    remote_hermes_agent: str = "/opt/ai-stack/hermes-agent"
    service: str = "hermes-gateway.service"
    expected_ovos_commit: str | None = None
    skip_local_validation: bool = False
    execute: bool = False
    report_file: Path | None = None
    required_env_vars: tuple[str, ...] = (
        "SUPABASE_URL",
        "SUPABASE_SECRET_KEY",
        "OVOS_DEFAULT_TENANT_ID",
        "OVOS_DEFAULT_OWNER_USER_ID",
        "OVOS_SUPABASE_SCHEMA",
    )


@dataclass
class DeploymentStep:
    name: str
    command: list[str] | None = None
    cwd: Path | None = None
    timeout: int = 120
    remote_script: str | None = None
    mutates: bool = False


@dataclass
class StepRecord:
    name: str
    status: str
    code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass
class DeploymentReport:
    started_at: str
    completed_at: str | None = None
    status: str = "planned"
    deployed_commit: str | None = None
    previous_remote_commit: str | None = None
    report_file: str | None = None
    steps: list[StepRecord] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "completed_at": self.completed_at,
            "deployed_commit": self.deployed_commit,
            "previous_remote_commit": self.previous_remote_commit,
            "report_file": self.report_file,
            "started_at": self.started_at,
            "status": self.status,
            "steps": [step.__dict__ for step in self.steps],
        }


def _tail(value: str, limit: int = 2000) -> str:
    return value[-limit:]


def _utc_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _ssh_command(config: DeploymentConfig, script: str) -> list[str]:
    return ["ssh", config.remote_host, "bash", "-lc", shlex.quote(script)]


def _default_local_ovos_python(local_ovos_core: Path) -> Path:
    configured = os.environ.get("OVOS_DEPLOY_PYTHON")
    if configured:
        return Path(configured)
    for candidate in (
        local_ovos_core / ".venv" / "bin" / "python",
        Path("/private/tmp/ovos-core-venv313/bin/python"),
    ):
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _local_ovos_python(config: DeploymentConfig) -> str:
    return str(
        config.local_ovos_python or _default_local_ovos_python(config.local_ovos_core)
    )


def _safe_remote_env_names(config: DeploymentConfig) -> str:
    names = " ".join(shlex.quote(name) for name in config.required_env_vars)
    env_file = shlex.quote(f"{config.remote_ovos_core}/.env.supabase")
    return (
        f"set -eu; test -f {env_file}; "
        f'for name in {names}; do grep -Eq "^${{name}}=" {env_file}; done; '
        "printf 'required OVOS env vars present\\n'"
    )


def _remote_python(config: DeploymentConfig) -> str:
    return f"{config.remote_hermes_agent}/venv/bin/python"


def _remote_hermes(config: DeploymentConfig) -> str:
    return f"{config.remote_hermes_agent}/venv/bin/hermes"


def _remote_base_env(config: DeploymentConfig) -> str:
    return (
        f"set -a; . {shlex.quote(config.remote_ovos_core + '/.env.supabase')}; set +a; "
        f"export PYTHONPATH={shlex.quote(config.remote_ovos_core)};"
    )


def _health_script(config: DeploymentConfig) -> str:
    service = shlex.quote(config.service)
    ovos = shlex.quote(config.remote_ovos_core)
    py = shlex.quote(_remote_python(config))
    expected = shlex.quote(config.expected_ovos_commit or "")
    return (
        "set -eu; "
        f"systemctl --user is-active --quiet {service}; "
        f"pgrep -af 'hermes_cli.main gateway run' >/dev/null; "
        f"{_safe_remote_env_names(config)}; "
        f"cd {ovos}; npx supabase migration list --linked >/tmp/hermes-deploy-migrations.txt; "
        f"grep -q 20260729130000 /tmp/hermes-deploy-migrations.txt; "
        f"{_remote_base_env(config)} "
        f"{py} - <<'PY'\n"
        "import json\n"
        "from ovos_core.hermes_plugin import handle_ovos_command\n"
        "payload = json.loads(handle_ovos_command('status --json'))\n"
        "if payload.get('overall') == 'Critical':\n"
        "    raise SystemExit('OVOS status is Critical')\n"
        "gateway = payload.get('gateway') or {}\n"
        "if gateway.get('running') is not True:\n"
        "    raise SystemExit('gateway is not running in OVOS status')\n"
        "print(json.dumps({'overall': payload.get('overall'), 'gateway': gateway.get('state')}))\n"
        "PY\n"
        f'test -z {expected} || test "$(git -C {ovos} rev-parse HEAD)" = {expected}; '
        "printf 'health ok\\n'"
    )


def _smoke_script(config: DeploymentConfig) -> str:
    py = shlex.quote(_remote_python(config))
    hermes = shlex.quote(_remote_hermes(config))
    fixture = shlex.quote(
        f"{config.remote_ovos_core}/tests/fixtures/hermes_mvp_events.json"
    )
    store = shlex.quote(
        f"/tmp/hermes-deploy-smoke-{config.expected_ovos_commit or 'current'}.json"
    )
    tenant = "00000000-0000-0000-0000-000000000101"
    return (
        "set -eu; "
        f"{hermes} --version >/dev/null; "
        f"{_remote_base_env(config)} "
        f"OVOS_EDE_LOCAL_STORE={store} {py} -m ovos_core.ede.cli journal ingest {fixture} --json "
        '| grep -q \'"execution_status": "not_executed"\'; '
        f"{_remote_base_env(config)} "
        f"OVOS_EDE_LOCAL_STORE={store} {py} -m ovos_core.ede.cli journal list --tenant {tenant} --json "
        "| grep -q '\"events\"'; "
        f"{_remote_base_env(config)} "
        f"OVOS_EDE_LOCAL_STORE={store} {py} -m ovos_core.ede.cli brief generate "
        f"--tenant {tenant} --date 2026-07-29 --json "
        '| grep -q \'"approved_state": "approved_not_executable"\'; '
        f"{_remote_base_env(config)} "
        f"{py} -m ovos_core.ede.cli execution targets list | grep -q 'live adapter: none'; "
        f"{_remote_base_env(config)} "
        f"{py} -m ovos_core.ede.cli execution controls status | grep -q 'Execution Safety Kernel'; "
        "printf 'smoke ok\\n'"
    )


class DeploymentPipeline:
    def __init__(
        self,
        config: DeploymentConfig,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or SubprocessCommandRunner()

    def resolve_expected_commit(self) -> str:
        if self.config.expected_ovos_commit:
            return self.config.expected_ovos_commit
        result = self.runner.run(
            ["git", "rev-parse", "origin/main"],
            cwd=self.config.local_ovos_core,
            timeout=30,
        )
        if not result.ok:
            raise RuntimeError(
                result.stderr.strip() or "could not resolve local origin/main"
            )
        return result.stdout.strip()

    def build_steps(self) -> list[DeploymentStep]:
        expected = self.config.expected_ovos_commit or self.resolve_expected_commit()
        config = DeploymentConfig(**{
            **self.config.__dict__,
            "expected_ovos_commit": expected,
        })
        steps: list[DeploymentStep] = []
        if not config.skip_local_validation:
            py = _local_ovos_python(config)
            steps.extend([
                DeploymentStep(
                    "local ovos compile",
                    [
                        py,
                        "-X",
                        "pycache_prefix=/private/tmp/ovos-core-pycache",
                        "-m",
                        "compileall",
                        "ovos_core",
                        "tests",
                    ],
                    cwd=config.local_ovos_core,
                    timeout=180,
                ),
                DeploymentStep(
                    "local ovos pytest",
                    [py, "-m", "pytest", "-q"],
                    cwd=config.local_ovos_core,
                    timeout=300,
                ),
                DeploymentStep(
                    "local ovos ruff",
                    [py, "-m", "ruff", "check", "."],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
                DeploymentStep(
                    "local ovos format check",
                    [py, "-m", "ruff", "format", "--check", "."],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
                DeploymentStep(
                    "local ovos mypy",
                    [py, "-m", "mypy", "ovos_core", "tests"],
                    cwd=config.local_ovos_core,
                    timeout=180,
                ),
                DeploymentStep(
                    "local ovos diff check",
                    ["git", "diff", "--check"],
                    cwd=config.local_ovos_core,
                    timeout=30,
                ),
                DeploymentStep(
                    "local supabase reset",
                    ["supabase", "db", "reset", "--local"],
                    cwd=config.local_ovos_core,
                    timeout=300,
                ),
                DeploymentStep(
                    "local ede pgtap base",
                    [
                        "psql",
                        "postgresql://postgres:postgres@127.0.0.1:55422/postgres",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-f",
                        "tests/db/ede_db_validation.sql",
                    ],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
                DeploymentStep(
                    "local ede pgtap patterns",
                    [
                        "psql",
                        "postgresql://postgres:postgres@127.0.0.1:55422/postgres",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-f",
                        "tests/db/ede_005_pattern_validation.sql",
                    ],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
                DeploymentStep(
                    "local ede pgtap planning",
                    [
                        "psql",
                        "postgresql://postgres:postgres@127.0.0.1:55422/postgres",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-f",
                        "tests/db/ede_006_planning_validation.sql",
                    ],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
                DeploymentStep(
                    "local ede pgtap safety kernel",
                    [
                        "psql",
                        "postgresql://postgres:postgres@127.0.0.1:55422/postgres",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-f",
                        "tests/db/ede_007a_execution_safety_validation.sql",
                    ],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
                DeploymentStep(
                    "local hermes mvp pgtap",
                    [
                        "psql",
                        "postgresql://postgres:postgres@127.0.0.1:55422/postgres",
                        "-v",
                        "ON_ERROR_STOP=1",
                        "-f",
                        "tests/db/hermes_mvp_daily_brief_validation.sql",
                    ],
                    cwd=config.local_ovos_core,
                    timeout=120,
                ),
            ])
        steps.extend([
            DeploymentStep(
                "verify local ovos main",
                remote_script=None,
                command=[
                    "bash",
                    "-lc",
                    (
                        "set -eu; "
                        'test "$(git rev-parse main)" = "$(git rev-parse origin/main)"; '
                        f'test "$(git rev-parse origin/main)" = {shlex.quote(expected)}'
                    ),
                ],
                cwd=config.local_ovos_core,
                timeout=30,
            ),
            DeploymentStep(
                "remote current commit",
                remote_script=(
                    f"set -eu; git -C {shlex.quote(config.remote_ovos_core)} rev-parse HEAD"
                ),
            ),
            DeploymentStep(
                "remote tracked clean",
                remote_script=(
                    f'set -eu; test -z "$(git -C {shlex.quote(config.remote_ovos_core)} '
                    'status --porcelain --untracked-files=no)"'
                ),
            ),
            DeploymentStep(
                "fetch latest ovos main",
                remote_script=(
                    f"set -eu; git -C {shlex.quote(config.remote_ovos_core)} "
                    f"fetch --force {shlex.quote(config.remote_ovos_repo_url)} "
                    "main:refs/remotes/hermes-deploy/main; "
                    f'test "$(git -C {shlex.quote(config.remote_ovos_core)} '
                    'rev-parse refs/remotes/hermes-deploy/main)" '
                    f"= {shlex.quote(expected)}"
                ),
                mutates=True,
                timeout=180,
            ),
            DeploymentStep(
                "pull latest ovos main",
                remote_script=(
                    f"set -eu; git -C {shlex.quote(config.remote_ovos_core)} switch main; "
                    f"git -C {shlex.quote(config.remote_ovos_core)} "
                    "reset --hard refs/remotes/hermes-deploy/main; "
                    f'test "$(git -C {shlex.quote(config.remote_ovos_core)} rev-parse HEAD)" '
                    f"= {shlex.quote(expected)}"
                ),
                mutates=True,
                timeout=180,
            ),
            DeploymentStep(
                "verify editable ovos install",
                remote_script=(
                    f"set -eu; cd {shlex.quote(config.remote_ovos_core)}; "
                    f"if {shlex.quote(_remote_python(config))} - <<'PY'\n"
                    "from pathlib import Path\n"
                    "import ovos_core\n"
                    f"expected = Path({config.remote_ovos_core!r}).resolve()\n"
                    "actual = Path(ovos_core.__file__).resolve()\n"
                    "raise SystemExit(0 if expected in actual.parents else 1)\n"
                    "PY\n"
                    "then printf 'editable OVOS install already active\\n'; "
                    f"else {shlex.quote(_remote_python(config))} -m pip install -e .; fi"
                ),
                mutates=True,
                timeout=300,
            ),
            DeploymentStep(
                "remote dry-run migrations",
                remote_script=(
                    f"set -eu; cd {shlex.quote(config.remote_ovos_core)}; "
                    "npx supabase db push --dry-run"
                ),
                timeout=300,
            ),
            DeploymentStep(
                "apply production migrations",
                remote_script=(
                    f"set -eu; cd {shlex.quote(config.remote_ovos_core)}; npx supabase db push"
                ),
                mutates=True,
                timeout=600,
            ),
            DeploymentStep(
                "restart gateway service",
                remote_script=(
                    f"set -eu; systemctl --user restart {shlex.quote(config.service)}"
                ),
                mutates=True,
                timeout=120,
            ),
            DeploymentStep(
                "wait for healthy service",
                remote_script=(
                    f"set -eu; for i in $(seq 1 30); do "
                    f"systemctl --user is-active --quiet {shlex.quote(config.service)} && exit 0; "
                    "sleep 2; done; systemctl --user status "
                    f"{shlex.quote(config.service)} --no-pager --lines=40; exit 1"
                ),
                timeout=90,
            ),
            DeploymentStep(
                "health verification",
                remote_script=_health_script(config),
                timeout=240,
            ),
            DeploymentStep(
                "smoke tests",
                remote_script=_smoke_script(config),
                timeout=240,
            ),
        ])
        return steps

    def plan(self) -> list[str]:
        lines: list[str] = []
        for step in self.build_steps():
            if step.remote_script:
                lines.append(
                    f"{step.name}: ssh {self.config.remote_host} {step.remote_script}"
                )
            elif step.command:
                prefix = f"(cd {step.cwd} && " if step.cwd else ""
                suffix = ")" if step.cwd else ""
                lines.append(
                    f"{step.name}: {prefix}{_shell_join(step.command)}{suffix}"
                )
        return lines

    def run(self) -> DeploymentReport:
        report = DeploymentReport(started_at=_utc_stamp())
        if not self.config.execute:
            report.status = "planned"
            report.completed_at = _utc_stamp()
            report.steps = [
                StepRecord(name=line, status="planned") for line in self.plan()
            ]
            self._write_report(report)
            return report

        expected = self.resolve_expected_commit()
        object.__setattr__(self.config, "expected_ovos_commit", expected)
        report.deployed_commit = expected
        for step in self.build_steps():
            result = self._run_step(step)
            record = StepRecord(
                name=step.name,
                status="passed" if result.ok else "failed",
                code=result.code,
                stdout_tail=_tail(result.stdout),
                stderr_tail=_tail(result.stderr),
            )
            report.steps.append(record)
            if step.name == "remote current commit" and result.ok:
                report.previous_remote_commit = result.stdout.strip()
            if not result.ok:
                report.status = "failed"
                report.completed_at = _utc_stamp()
                self._write_report(report)
                return report
        report.status = "healthy"
        report.completed_at = _utc_stamp()
        self._write_report(report)
        return report

    def _run_step(self, step: DeploymentStep) -> CommandResult:
        if step.remote_script:
            return self.runner.run(
                _ssh_command(self.config, step.remote_script),
                timeout=step.timeout,
            )
        if step.command is None:
            return CommandResult(2, stderr="step has no command")
        return self.runner.run(step.command, cwd=step.cwd, timeout=step.timeout)

    def _write_report(self, report: DeploymentReport) -> None:
        if self.config.report_file is None:
            return
        self.config.report_file.parent.mkdir(parents=True, exist_ok=True)
        report.report_file = str(self.config.report_file)
        self.config.report_file.write_text(
            json.dumps(report.to_jsonable(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def cmd_deploy(args: Any) -> int:
    config = DeploymentConfig(
        remote_host=args.remote_host,
        local_ovos_core=Path(args.local_ovos_core),
        local_ovos_python=Path(args.local_ovos_python)
        if args.local_ovos_python
        else None,
        remote_ovos_repo_url=args.remote_ovos_repo_url,
        remote_ovos_core=args.remote_ovos_core,
        remote_hermes_agent=args.remote_hermes_agent,
        service=args.service,
        expected_ovos_commit=args.expected_ovos_commit,
        skip_local_validation=args.skip_local_validation,
        execute=args.execute,
        report_file=Path(args.report_file) if args.report_file else None,
    )
    report = DeploymentPipeline(config).run()
    print(json.dumps(report.to_jsonable(), indent=2, sort_keys=True))
    return 0 if report.status in {"planned", "healthy"} else 1
