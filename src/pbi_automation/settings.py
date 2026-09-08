from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class FabricSettings:
    workspace_id: str
    workspace_url: str
    git_folder: str
    github_repo: str
    branch: str

    @property
    def workspace_open_url(self) -> str:
        return (
            self.workspace_url
            or f"https://app.fabric.microsoft.com/groups/{self.workspace_id}/list?experience=fabric-developer"
        )


def repo_root_from(start: Path | None = None) -> Path:
    here = start or Path.cwd()
    for candidate in [here, *here.parents]:
        if (candidate / "config" / "fabric.yaml").exists() or (
            candidate / "config" / "dashboard.yaml"
        ).exists():
            return candidate
    return here


def load_fabric_settings(root: Path | None = None) -> FabricSettings:
    root = root or repo_root_from()
    load_dotenv(root / ".env")
    raw: dict[str, Any] = {}
    config_path = root / "config" / "fabric.yaml"
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    workspace_id = os.getenv("FABRIC_WORKSPACE_ID", "").strip() or str(raw.get("workspace_id") or "")
    if not workspace_id:
        raise RuntimeError("FABRIC_WORKSPACE_ID is missing. Set it in .env or config/fabric.yaml.")
    return FabricSettings(
        workspace_id=workspace_id,
        workspace_url=str(raw.get("workspace_url") or ""),
        git_folder=str(raw.get("git_folder") or "workspace"),
        github_repo=str(raw.get("github_repo") or "Tamadhi/powerbi_automation"),
        branch=str(raw.get("branch") or "main"),
    )
