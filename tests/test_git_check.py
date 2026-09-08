import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from pbi_automation.git_check import commit_and_push, inspect_git
from pbi_automation.launch import launch


def test_inspect_git_finds_existing_remote() -> None:
    repo = Path(__file__).resolve().parents[1]
    info = inspect_git(repo)
    assert info.inside_work_tree
    assert info.remote_url
    assert "powerbi_automation" in info.remote_url


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_commit_and_push_reports_noop_when_clean(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    tracked = tmp_path / "workspace"
    tracked.mkdir()
    (tracked / "keep.txt").write_text("ok\n", encoding="utf-8")
    _git(tmp_path, "add", "workspace")
    _git(tmp_path, "commit", "-m", "seed")

    result = commit_and_push(tmp_path, [tracked], "noop", push=True)
    assert result.committed is False
    assert result.pushed is False


def test_launch_does_not_claim_commit_or_push_on_noop() -> None:
    repo = Path(__file__).resolve().parents[1]
    spec = MagicMock()
    spec.name = "NorthwindSales"
    generate_result = MagicMock()
    generate_result.spec = spec
    generate_result.output_dir = repo / "workspace"
    generate_result.pbip_path = repo / "workspace" / "NorthwindSales.pbip"
    generate_result.report_dir = repo / "workspace" / "NorthwindSales.Report"

    noop = MagicMock(committed=False, pushed=False)
    with (
        patch("pbi_automation.launch.commit_and_push", return_value=noop),
        patch("pbi_automation.launch.launch_fabric") as fabric,
    ):
        fabric.return_value.message = "fabric skipped"
        text = launch(repo, generate_result, desktop=False, commit=True, push=True, fabric=True)

    assert "No git changes to commit." in text
    assert "Skipped push; nothing new was committed." in text
    assert "Committed generated workspace artifacts." not in text
    assert "Pushed to the existing git remote." not in text

