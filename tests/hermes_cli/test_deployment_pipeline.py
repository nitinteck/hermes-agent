from __future__ import annotations

import json
from pathlib import Path

from hermes_cli.deployment import (
    CommandResult,
    DeploymentConfig,
    DeploymentPipeline,
    _ssh_command,
)


class FakeRunner:
    def __init__(self, failures: dict[str, CommandResult] | None = None) -> None:
        self.failures = failures or {}
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int = 120,
        input_text: str | None = None,
    ) -> CommandResult:
        del cwd, timeout, input_text
        self.calls.append(args)
        command = " ".join(args)
        for token, result in self.failures.items():
            if token in command:
                return result
        if "rev-parse HEAD" in command:
            return CommandResult(0, "previous-sha\n", "")
        if "rev-parse origin/main" in command:
            return CommandResult(0, "target-sha\n", "")
        return CommandResult(0, "ok\n", "")


def _config(tmp_path: Path, *, execute: bool = False) -> DeploymentConfig:
    return DeploymentConfig(
        execute=execute,
        expected_ovos_commit="target-sha",
        local_ovos_core=tmp_path,
        report_file=tmp_path / "deploy-report.json",
        skip_local_validation=True,
    )


def test_deploy_defaults_to_dry_run_plan(tmp_path: Path) -> None:
    runner = FakeRunner()
    pipeline = DeploymentPipeline(_config(tmp_path), runner=runner)

    report = pipeline.run()

    assert report.status == "planned"
    assert runner.calls == []
    assert any("remote dry-run migrations" in step.name for step in report.steps)
    assert (
        json.loads((tmp_path / "deploy-report.json").read_text())["status"] == "planned"
    )


def test_execute_stops_before_mutating_steps_when_remote_clean_check_fails(
    tmp_path: Path,
) -> None:
    runner = FakeRunner(
        failures={
            "status --porcelain": CommandResult(1, "", "tracked files are dirty"),
        }
    )
    pipeline = DeploymentPipeline(_config(tmp_path, execute=True), runner=runner)

    report = pipeline.run()
    commands = [" ".join(call) for call in runner.calls]

    assert report.status == "failed"
    assert any(
        step.name == "remote tracked clean" and step.status == "failed"
        for step in report.steps
    )
    assert not any("systemctl --user restart" in command for command in commands)
    assert not any(
        "supabase db push" in command and "--dry-run" not in command
        for command in commands
    )


def test_execute_records_previous_and_deployed_commit_when_healthy(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    pipeline = DeploymentPipeline(_config(tmp_path, execute=True), runner=runner)

    report = pipeline.run()

    assert report.status == "healthy"
    assert report.previous_remote_commit == "previous-sha"
    assert report.deployed_commit == "target-sha"
    commands = [" ".join(call) for call in runner.calls]
    assert any("npx supabase db push --dry-run" in command for command in commands)
    assert any(
        "npx supabase db push" in command and "--dry-run" not in command
        for command in commands
    )
    assert any(
        "systemctl --user restart hermes-gateway.service" in command
        for command in commands
    )


def test_plan_includes_safety_kernel_and_non_execution_smoke(tmp_path: Path) -> None:
    pipeline = DeploymentPipeline(_config(tmp_path), runner=FakeRunner())

    plan = "\n".join(pipeline.plan())

    assert "execution targets list | grep -q 'live adapter: none'" in plan
    assert "execution controls status | grep -q 'Execution Safety Kernel'" in plan
    assert "approved_not_executable" in plan
    assert "not_executed" in plan


def test_health_requires_hermes_mvp_migration(tmp_path: Path) -> None:
    pipeline = DeploymentPipeline(_config(tmp_path), runner=FakeRunner())

    plan = "\n".join(pipeline.plan())

    assert "grep -q 20260729130000" in plan


def test_ssh_command_quotes_remote_script_as_single_shell_argument() -> None:
    command = _ssh_command(DeploymentConfig(), "set -eu; false; echo unsafe")

    assert command[:4] == ["ssh", "hermes-vps", "bash", "-lc"]
    assert command[4] == "'set -eu; false; echo unsafe'"


def test_remote_fetch_uses_verified_local_bundle_by_default(
    tmp_path: Path,
) -> None:
    pipeline = DeploymentPipeline(_config(tmp_path), runner=FakeRunner())

    plan = "\n".join(pipeline.plan())

    assert "create local ovos deploy bundle" in plan
    assert "copy ovos deploy bundle" in plan
    assert "fetch --force /tmp/hermes-ovos-target-sha.bundle" in plan
    assert "refs/remotes/hermes-deploy/main" in plan
    assert "origin main" not in plan


def test_remote_fetch_can_use_explicit_repo_url(tmp_path: Path) -> None:
    config = DeploymentConfig(
        execute=False,
        expected_ovos_commit="target-sha",
        local_ovos_core=tmp_path,
        remote_ovos_repo_url="https://example.test/ovos-core.git",
        skip_local_validation=True,
    )
    pipeline = DeploymentPipeline(config, runner=FakeRunner())

    plan = "\n".join(pipeline.plan())

    assert "create local ovos deploy bundle" not in plan
    assert "fetch --force https://example.test/ovos-core.git" in plan
