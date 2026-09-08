from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from pbi_automation.settings import FabricSettings, load_fabric_settings

FABRIC_API = "https://api.fabric.microsoft.com/v1"
TOKEN_SCOPE = "https://api.fabric.microsoft.com/.default"


class FabricError(RuntimeError):
    pass


@dataclass
class FabricLaunchResult:
    workspace_id: str
    connected: bool
    report_id: str | None
    report_url: str | None
    message: str


def _token() -> str:
    try:
        from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
    except ImportError as exc:
        raise FabricError("azure-identity is required for Fabric launch.") from exc
    try:
        return DefaultAzureCredential(exclude_interactive_browser_credential=True).get_token(
            TOKEN_SCOPE
        ).token
    except Exception:
        print("Opening a browser to sign in to Microsoft Fabric...")
        return InteractiveBrowserCredential().get_token(TOKEN_SCOPE).token


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=FABRIC_API,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"},
        timeout=60.0,
    )


def _poll_operation(client: httpx.Client, operation_id: str) -> dict:
    deadline = time.time() + 300
    while time.time() < deadline:
        response = client.get(f"/operations/{operation_id}")
        response.raise_for_status()
        body = response.json()
        status = body.get("status")
        if status in {"Succeeded", "Completed"}:
            return body
        if status in {"Failed", "Undefined"}:
            raise FabricError(f"Fabric operation failed: {body}")
        retry_after = int(response.headers.get("Retry-After", "5"))
        time.sleep(retry_after)
    raise FabricError("Timed out waiting for Fabric Git sync.")


def _connect_instructions(settings: FabricSettings) -> str:
    return (
        "Fabric workspace is not connected to Git yet. Connect it once, then re-run launch:\n"
        f"1. Open {settings.workspace_open_url}\n"
        "2. Source control > Connect to GitHub.\n"
        f"3. Repository: {settings.github_repo}\n"
        f"4. Branch: {settings.branch}\n"
        f"5. Git folder: {settings.git_folder}\n"
        f"Workspace ID: {settings.workspace_id}"
    )


def _report_url(settings: FabricSettings, report_id: str) -> str:
    return (
        f"https://app.fabric.microsoft.com/groups/{settings.workspace_id}"
        f"/reports/{report_id}?experience=fabric-developer"
    )


def fabric_status() -> str:
    settings = load_fabric_settings()
    lines = [
        f"Fabric workspace: {settings.workspace_id}",
        f"Open workspace: {settings.workspace_open_url}",
        f"GitHub repo: {settings.github_repo} ({settings.branch})",
        f"Git folder: {settings.git_folder}",
    ]
    try:
        with _client() as client:
            connection = client.get(f"/workspaces/{settings.workspace_id}/git/connection")
            if connection.status_code in {400, 404}:
                lines.append("Git connection: not connected")
                lines.append(_connect_instructions(settings))
                return "\n".join(lines)
            connection.raise_for_status()
            body = connection.json()
            lines.append(f"Git connection: {body}")
            git_status = client.get(f"/workspaces/{settings.workspace_id}/git/status")
            if git_status.is_success:
                lines.append(f"Git sync status: {git_status.json()}")
    except Exception as exc:
        lines.append(f"Fabric API not reachable yet: {exc}")
        lines.append("Sign in with a Microsoft account that can open the workspace, then retry.")
    return "\n".join(lines)


def launch_fabric(display_name: str) -> FabricLaunchResult:
    settings = load_fabric_settings()
    with _client() as client:
        workspace_id = settings.workspace_id
        connection = client.get(f"/workspaces/{workspace_id}/git/connection")
        if connection.status_code in {400, 404}:
            return FabricLaunchResult(
                workspace_id=workspace_id,
                connected=False,
                report_id=None,
                report_url=None,
                message=_connect_instructions(settings),
            )
        if connection.status_code >= 400:
            raise FabricError(f"Git connection check failed ({connection.status_code}): {connection.text}")

        status = client.get(f"/workspaces/{workspace_id}/git/status")
        status.raise_for_status()
        git_status = status.json()
        remote_hash = git_status.get("remoteCommitHash")
        workspace_head = git_status.get("workspaceHead")
        if not remote_hash:
            return FabricLaunchResult(
                workspace_id=workspace_id,
                connected=True,
                report_id=None,
                report_url=None,
                message="Git is connected but remoteCommitHash is empty. Push commits first, then retry.",
            )

        update = client.post(
            f"/workspaces/{workspace_id}/git/updateFromGit",
            json={
                "remoteCommitHash": remote_hash,
                "workspaceHead": workspace_head,
                "options": {"allowOverrideItems": True},
            },
        )
        if update.status_code not in {200, 202}:
            raise FabricError(f"updateFromGit failed ({update.status_code}): {update.text}")
        operation_id = update.headers.get("x-ms-operation-id")
        if operation_id:
            _poll_operation(client, operation_id)

        items = client.get(f"/workspaces/{workspace_id}/items", params={"type": "Report"})
        items.raise_for_status()
        report_id = None
        for item in items.json().get("value", []):
            if item.get("displayName") == display_name:
                report_id = item.get("id")
                break
        report_url = _report_url(settings, report_id) if report_id else settings.workspace_open_url
        message = (
            f"Fabric workspace synced from Git.\nOpen report: {report_url}"
            if report_id
            else (
                "Fabric workspace synced from Git. Open the workspace and look for the report:\n"
                f"{settings.workspace_open_url}"
            )
        )
        return FabricLaunchResult(
            workspace_id=workspace_id,
            connected=True,
            report_id=report_id,
            report_url=report_url,
            message=message,
        )
