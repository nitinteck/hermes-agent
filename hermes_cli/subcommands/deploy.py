"""``hermes deploy`` subcommand parser."""

from __future__ import annotations

from typing import Callable


def build_deploy_parser(subparsers, *, cmd_deploy: Callable) -> None:
    """Attach the deployment pipeline command to ``subparsers``."""
    deploy = subparsers.add_parser(
        "deploy",
        help="Deploy validated OVOS milestones to the Hermes VPS",
        description=(
            "Run the fail-closed Hermes deployment pipeline. Defaults to dry-run "
            "planning; pass --execute to mutate the VPS."
        ),
    )
    deploy.add_argument(
        "--execute",
        action="store_true",
        help="Actually run deployment steps on the VPS. Without this, only a plan is printed.",
    )
    deploy.add_argument("--remote-host", default="hermes-vps", help="SSH host alias.")
    deploy.add_argument(
        "--remote-ovos-core",
        default="/opt/ai-stack/ovos-core",
        help="OVOS Core checkout on the VPS.",
    )
    deploy.add_argument(
        "--remote-hermes-agent",
        default="/opt/ai-stack/hermes-agent",
        help="Hermes Agent checkout on the VPS.",
    )
    deploy.add_argument(
        "--local-ovos-core",
        default="/Users/nitinteckchandani/Projects/Hermes-Build/ovos-core",
        help="Local OVOS Core checkout used for validation and expected commit.",
    )
    deploy.add_argument(
        "--local-ovos-python",
        default=None,
        help=(
            "Python interpreter with OVOS dev dependencies. Defaults to "
            "OVOS_DEPLOY_PYTHON, the local OVOS venv when present, then the "
            "current Python."
        ),
    )
    deploy.add_argument(
        "--remote-ovos-repo-url",
        default="https://github.com/nitinteck/ovos-core.git",
        help="Read-only OVOS Core repository URL used by the VPS fetch step.",
    )
    deploy.add_argument(
        "--service",
        default="hermes-gateway.service",
        help="User-scoped systemd service to restart.",
    )
    deploy.add_argument(
        "--expected-ovos-commit",
        default=None,
        help="Required OVOS commit SHA after pulling main. Defaults to local origin/main.",
    )
    deploy.add_argument(
        "--skip-local-validation",
        action="store_true",
        help="Skip local validation commands. Intended only after a fresh validation gate.",
    )
    deploy.add_argument(
        "--report-file",
        default=None,
        help="Optional local JSON deployment report path.",
    )
    deploy.set_defaults(func=cmd_deploy)
