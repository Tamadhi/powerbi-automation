from pathlib import Path
from unittest.mock import patch

from pbi_automation.desktop import find_pbi_desktop, open_in_desktop


def test_open_in_desktop_uses_found_exe(tmp_path: Path) -> None:
    pbip = tmp_path / "Demo.pbip"
    pbip.write_text("{}", encoding="utf-8")
    fake_exe = tmp_path / "PBIDesktop.exe"
    fake_exe.write_text("", encoding="utf-8")

    with (
        patch("pbi_automation.desktop.find_pbi_desktop", return_value=fake_exe),
        patch("pbi_automation.desktop.subprocess.Popen") as popen,
    ):
        message = open_in_desktop(pbip)

    popen.assert_called_once()
    assert pbip.name in message


def test_find_pbi_desktop_returns_none_when_missing() -> None:
    with patch("pbi_automation.desktop._candidate_exes", return_value=[Path("Z:/missing/PBIDesktop.exe")]):
        assert find_pbi_desktop() is None
