from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class DesktopError(RuntimeError):
    pass


def _candidate_exes() -> list[Path]:
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    local_app = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        program_files / "Microsoft Power BI Desktop" / "bin" / "PBIDesktop.exe",
        program_files_x86 / "Microsoft Power BI Desktop" / "bin" / "PBIDesktop.exe",
        local_app / "Microsoft" / "WindowsApps" / "PBIDesktop.exe",
    ]
    which = shutil.which("PBIDesktop")
    if which:
        candidates.insert(0, Path(which))
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\PBIDesktop.exe",
        ) as key:
            value, _ = winreg.QueryValueEx(key, None)
            if value:
                candidates.insert(0, Path(value))
    except OSError:
        pass
    return candidates


def find_pbi_desktop() -> Path | None:
    seen: set[Path] = set()
    for candidate in _candidate_exes():
        resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def open_in_desktop(pbip_path: Path) -> str:
    if not pbip_path.exists():
        raise DesktopError(f"PBIP file not found: {pbip_path}")

    exe = find_pbi_desktop()
    if exe:
        subprocess.Popen(
            [str(exe), str(pbip_path)],
            cwd=str(pbip_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Opened {pbip_path.name} in Power BI Desktop.\nEnable Preview: PBIP save + TMDL format, then refresh the Northwind OData source."

    if os.name == "nt":
        os.startfile(str(pbip_path))  # type: ignore[attr-defined]
        return (
            f"Opened {pbip_path.name} with the default Windows app. "
            "Install Power BI Desktop if it does not launch."
        )

    raise DesktopError(
        "Power BI Desktop was not found. Install it from Microsoft Store or "
        "https://aka.ms/pbidesktop, then re-run `pbi-auto launch`."
    )
