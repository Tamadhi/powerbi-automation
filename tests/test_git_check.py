from pathlib import Path

from pbi_automation.git_check import inspect_git


def test_inspect_git_finds_existing_remote() -> None:
    repo = Path(__file__).resolve().parents[1]
    info = inspect_git(repo)
    assert info.inside_work_tree
    assert info.remote_url
    assert "powerbi_automation" in info.remote_url
