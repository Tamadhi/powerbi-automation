from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(RuntimeError):
    pass


@dataclass
class GitInfo:
    root: Path
    inside_work_tree: bool
    branch: str | None
    remote_name: str | None
    remote_url: str | None
    dirty: bool
    porcelain: str

    @property
    def connected(self) -> bool:
        return self.inside_work_tree and bool(self.remote_url)


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def _git(args: list[str], cwd: Path) -> str:
    result = _run(["git", *args], cwd)
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip() or "git command failed")
    return result.stdout.strip()


def inspect_git(repo_root: Path) -> GitInfo:
    probe = _run(["git", "rev-parse", "--is-inside-work-tree"], repo_root)
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return GitInfo(
            root=repo_root,
            inside_work_tree=False,
            branch=None,
            remote_name=None,
            remote_url=None,
            dirty=False,
            porcelain="",
        )

    branch = _git(["branch", "--show-current"], repo_root) or None
    remotes = _git(["remote"], repo_root).splitlines()
    remote_name = "origin" if "origin" in remotes else (remotes[0] if remotes else None)
    remote_url = _git(["remote", "get-url", remote_name], repo_root) if remote_name else None
    porcelain = _git(["status", "--porcelain"], repo_root)
    return GitInfo(
        root=repo_root,
        inside_work_tree=True,
        branch=branch,
        remote_name=remote_name,
        remote_url=remote_url,
        dirty=bool(porcelain),
        porcelain=porcelain,
    )


def format_git_status(info: GitInfo) -> str:
    if not info.inside_work_tree:
        return "Not a git repository. Initialize one before launch."
    lines = [
        f"Git repo: {info.root}",
        f"Branch: {info.branch or '(detached)'}",
    ]
    if info.connected:
        lines.append(f"Remote: {info.remote_name} -> {info.remote_url}")
        lines.append("Already connected to a git remote. The generator will reuse it.")
    else:
        lines.append("No git remote configured. Add origin before `pbi-auto launch`.")
    if info.dirty:
        lines.append("Working tree has uncommitted changes.")
    else:
        lines.append("Working tree is clean.")
    return "\n".join(lines)


def commit_and_push(repo_root: Path, paths: list[Path], message: str, *, push: bool) -> GitInfo:
    info = inspect_git(repo_root)
    if not info.inside_work_tree:
        raise GitError("Not a git repository.")
    rels = [str(path.relative_to(repo_root)) if path.is_absolute() else str(path) for path in paths]
    _git(["add", "--", *rels], repo_root)
    status = _git(["status", "--porcelain"], repo_root)
    if not status:
        return inspect_git(repo_root)
    _git(["commit", "-m", message], repo_root)
    if push:
        if not info.remote_name:
            raise GitError("No git remote configured; cannot push.")
        branch = info.branch or "HEAD"
        _git(["push", "-u", info.remote_name, branch], repo_root)
    return inspect_git(repo_root)
