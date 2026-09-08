from __future__ import annotations

import argparse
from pathlib import Path

from pbi_automation.fabric import fabric_status
from pbi_automation.generate import generate
from pbi_automation.git_check import format_git_status, inspect_git
from pbi_automation.launch import launch
from pbi_automation.settings import load_fabric_settings, repo_root_from


def _repo_root() -> Path:
    return repo_root_from(Path.cwd())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pbi-auto",
        description="Generate a Power BI semantic model + report (PBIP) and publish it with Git to a Fabric workspace.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to dashboard YAML (default: config/dashboard.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output folder for the PBIP project (default: workspace/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("git-status", help="Show whether this folder is already connected to a git remote.")
    sub.add_parser("status", help="Show Git remote + Fabric workspace connection.")
    generate_parser = sub.add_parser("generate", help="Write TMDL semantic model + PBIR report + theme into workspace/.")
    launch_parser = sub.add_parser(
        "launch",
        help="Generate the PBIP, push to GitHub, and sync the Fabric workspace.",
    )
    for subparser in (generate_parser, launch_parser):
        subparser.add_argument(
            "--template",
            type=Path,
            default=None,
            help="PBIR dashboard template folder. Layout is copied; fields are rebound to the generated model.",
        )
    launch_parser.add_argument(
        "--desktop",
        action="store_true",
        help="Also open the generated .pbip in Power BI Desktop.",
    )
    launch_parser.add_argument("--no-commit", action="store_true", help="Do not create a git commit.")
    launch_parser.add_argument("--no-push", action="store_true", help="Commit locally but do not push.")
    launch_parser.add_argument(
        "--no-fabric",
        action="store_true",
        help="Skip Fabric workspace sync.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    config_path = args.config or (repo_root / "config" / "dashboard.yaml")
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    output_dir = args.output or (repo_root / "workspace")
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    if args.command == "git-status":
        print(format_git_status(inspect_git(repo_root)))
        return 0

    if args.command == "status":
        settings = load_fabric_settings(repo_root)
        print(format_git_status(inspect_git(repo_root)))
        print(f"Power BI / Fabric workspace: {settings.workspace_id}")
        print(f"Open: {settings.workspace_open_url}")
        print(fabric_status())
        return 0

    result = generate(
        repo_root,
        config_path,
        output_dir,
        template=getattr(args, "template", None),
    )
    print(f"Wrote semantic model: {result.model_dir}")
    print(f"Wrote report: {result.report_dir}")
    print(f"Wrote project shortcut: {result.pbip_path}")

    if args.command == "generate":
        print("Next: pbi-auto launch   (push + Fabric Git sync)")
        return 0

    print(
        launch(
            repo_root,
            result,
            desktop=args.desktop,
            commit=not args.no_commit,
            push=not args.no_push,
            fabric=not args.no_fabric,
        )
    )
    return 0
