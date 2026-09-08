from pathlib import Path

from pbi_automation.generate import generate


def test_generate_writes_tmdl_pbir_and_theme(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    result = generate(repo, repo / "config" / "dashboard.yaml", tmp_path)

    assert (result.model_dir / "definition.pbism").exists()
    assert (result.model_dir / "definition" / "tables" / "Order_Details.tmdl").exists()
    assert "Total Sales" in (result.model_dir / "definition" / "tables" / "Order_Details.tmdl").read_text(
        encoding="utf-8"
    )
    assert (result.report_dir / "definition.pbir").exists()
    assert (result.report_dir / "definition" / "report.json").exists()
    assert (result.report_dir / "StaticResources" / "RegisteredResources" / "corporate.json").exists()
    assert result.pbip_path.exists()
    pbir = (result.report_dir / "definition.pbir").read_text(encoding="utf-8")
    assert "../NorthwindSales.SemanticModel" in pbir
