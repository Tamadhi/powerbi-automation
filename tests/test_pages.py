from pathlib import Path

import pytest

from pbi_automation.models import ConfigError, first_page, load_spec
from pbi_automation.pbir import _builtin_report
from pbi_automation.rebind import rebind_report


def test_load_spec_rejects_empty_pages(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    config = tmp_path / "dashboard.yaml"
    config.write_text(
        "\n".join(
            [
                "name: EmptyPages",
                "theme: templates/themes/corporate.json",
                "source:",
                "  type: odata",
                "  url: https://services.odata.org/V4/Northwind/Northwind.svc/",
                "pages: {}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="no pages"):
        load_spec(config, repo)


def test_builtin_and_rebind_reject_empty_page_list(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    spec = load_spec(repo / "config" / "dashboard.yaml", repo)
    spec.pages = []
    with pytest.raises(ConfigError, match="no pages"):
        first_page(spec)
    with pytest.raises(ConfigError, match="no pages"):
        _builtin_report(spec, tmp_path / "report", "corporate.json")
    with pytest.raises(ConfigError, match="no pages"):
        rebind_report(tmp_path / "report", spec)
