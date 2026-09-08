import json
from pathlib import Path

from pbi_automation.generate import generate
from pbi_automation.models import load_spec
from pbi_automation.rebind import rebind_visual


def test_rebind_rewrites_chart_and_card_fields() -> None:
    repo = Path(__file__).resolve().parents[1]
    page = load_spec(repo / "config" / "dashboard.yaml", repo).pages[0]
    card = {
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {
                    "Data": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": "Old"}},
                                        "Property": "Revenue",
                                    }
                                },
                                "queryRef": "Old.Revenue",
                                "nativeQueryRef": "Revenue",
                            }
                        ]
                    }
                }
            },
        }
    }
    chart = {
        "visual": {
            "visualType": "clusteredBarChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Entity": "Old"}},
                                        "Property": "Region",
                                    }
                                },
                                "queryRef": "Old.Region",
                                "nativeQueryRef": "Region",
                            }
                        ]
                    },
                    "Y": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": "Old"}},
                                        "Property": "Revenue",
                                    }
                                },
                                "queryRef": "Old.Revenue",
                                "nativeQueryRef": "Revenue",
                            }
                        ]
                    },
                },
                "sortDefinition": {"sort": [{"field": {}, "direction": "Descending"}]},
            },
        }
    }
    rebind_visual(card, page)
    rebind_visual(chart, page)
    assert card["visual"]["query"]["queryState"]["Data"]["projections"][0]["queryRef"] == (
        page.cards[0].query_ref
    )
    assert chart["visual"]["query"]["queryState"]["Category"]["projections"][0]["queryRef"] == (
        page.chart.x.query_ref
    )
    assert chart["visual"]["query"]["queryState"]["Y"]["projections"][0]["queryRef"] == (
        page.chart.y.query_ref
    )


def test_generate_from_dashboard_template(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    result = generate(
        repo,
        repo / "config" / "dashboard.yaml",
        tmp_path,
        template=repo / "templates" / "dashboard",
    )
    visuals = list((result.report_dir / "definition" / "pages").glob("**/visuals/*/visual.json"))
    assert visuals
    joined = "\n".join(path.read_text(encoding="utf-8") for path in visuals)
    assert "Order_Details.Total Sales" in joined
    assert "Customers.Country" in joined
    pbir = json.loads((result.report_dir / "definition.pbir").read_text(encoding="utf-8"))
    assert pbir["datasetReference"]["byPath"]["path"] == "../NorthwindSales.SemanticModel"
