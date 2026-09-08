from __future__ import annotations

from pathlib import Path

from pbi_automation.desktop import DesktopError, open_in_desktop
from pbi_automation.fabric import FabricError, launch_fabric
from pbi_automation.generate import GenerateResult
from pbi_automation.git_check import GitError, commit_and_push, format_git_status, inspect_git
from pbi_automation.settings import load_fabric_settings


def launch(
    repo_root: Path,
    result: GenerateResult,
    *,
    desktop: bool = False,
    commit: bool = True,
    push: bool = True,
    fabric: bool = True,
) -> str:
    settings = load_fabric_settings(repo_root)
    lines = [
        format_git_status(inspect_git(repo_root)),
        f"Fabric workspace: {settings.workspace_id}",
        f"Open workspace: {settings.workspace_open_url}",
    ]

    if desktop:
        try:
            lines.append(open_in_desktop(result.pbip_path))
        except DesktopError as exc:
            lines.append(str(exc))
            pbir = result.report_dir / "definition.pbir"
            lines.append(f"You can also open this file in Power BI Desktop: {pbir}")

    if commit:
        try:
            git_result = commit_and_push(
                repo_root,
                [result.output_dir],
                f"Generate {result.spec.name} PBIP semantic model and report.",
                push=push,
            )
            if git_result.committed:
                lines.append("Committed generated workspace artifacts.")
            else:
                lines.append("No git changes to commit.")
            if push:
                if git_result.pushed:
                    lines.append("Pushed to the existing git remote.")
                else:
                    lines.append("Skipped push; nothing new was committed.")
        except GitError as exc:
            lines.append(f"Git step skipped/failed: {exc}")
    elif push:
        lines.append("Push requested without --commit; skipping git push.")

    if fabric:
        try:
            fabric_result = launch_fabric(result.spec.name)
            lines.append(fabric_result.message)
        except FabricError as exc:
            lines.append(f"Fabric launch not completed: {exc}")

    return "\n".join(lines)
