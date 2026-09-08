from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pbi_automation.io_util import write_json
from pbi_automation.models import DashboardSpec, FieldRef, PageSpec, first_page

CHART_TYPES = {
    "barChart",
    "clusteredBarChart",
    "columnChart",
    "clusteredColumnChart",
    "lineChart",
    "areaChart",
    "pieChart",
    "donutChart",
}
CARD_TYPES = {"cardVisual", "card", "multiRowCard"}


def resolve_template(path: Path) -> Path:
    if (path / "definition" / "pages").exists() or (path / "definition.pbir").exists():
        return path
    reports = sorted(path.glob("*.Report"))
    if len(reports) == 1:
        return reports[0]
    raise FileNotFoundError(
        f"No PBIR template found at {path}. Pass a *.Report folder or a folder that contains one."
    )


def _field_payload(ref: FieldRef) -> dict[str, Any]:
    kind = "Measure" if ref.kind == "measure" else "Column"
    return {
        kind: {
            "Expression": {"SourceRef": {"Entity": ref.table}},
            "Property": ref.name,
        }
    }


def _apply_ref(projection: dict[str, Any], ref: FieldRef) -> None:
    projection["field"] = _field_payload(ref)
    projection["queryRef"] = ref.query_ref
    projection["nativeQueryRef"] = ref.name


def _apply_list(projections: list[dict[str, Any]], refs: Iterable[FieldRef]) -> None:
    refs_list = list(refs)
    for index, projection in enumerate(projections):
        if index >= len(refs_list):
            break
        _apply_ref(projection, refs_list[index])


def _set_sort(query: dict[str, Any], ref: FieldRef) -> None:
    sort_def = query.get("sortDefinition")
    if not isinstance(sort_def, dict):
        return
    for item in sort_def.get("sort") or []:
        if isinstance(item, dict):
            item["field"] = _field_payload(ref)


def _set_textbox_title(visual: dict[str, Any], title: str) -> None:
    try:
        runs = visual["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"]
        if runs:
            runs[0]["value"] = title
    except (KeyError, IndexError, TypeError):
        return


def rebind_visual(payload: dict[str, Any], page: PageSpec) -> None:
    visual = payload.get("visual") or {}
    visual_type = visual.get("visualType")
    if visual_type == "textbox":
        _set_textbox_title(visual, page.title)
        return

    query = visual.get("query") or {}
    state = query.get("queryState") or {}
    if visual_type in CARD_TYPES:
        role = "Data" if "Data" in state else "Fields"
        if role in state:
            _apply_list(state[role].get("projections") or [], page.cards)
    elif visual_type == "slicer" and "Values" in state:
        _apply_list(state["Values"].get("projections") or [], [page.slicer])
    elif visual_type in CHART_TYPES:
        if "Category" in state:
            _apply_list(state["Category"].get("projections") or [], [page.chart.x])
        if "Y" in state:
            _apply_list(state["Y"].get("projections") or [], [page.chart.y])
        _set_sort(query, page.chart.y)
    elif visual_type in {"tableEx", "table"} and "Values" in state:
        _apply_list(state["Values"].get("projections") or [], page.table)


def rebind_report(report_dir: Path, spec: DashboardSpec) -> int:
    page = first_page(spec)
    updated = 0
    visuals_root = report_dir / "definition" / "pages"
    if not visuals_root.exists():
        return 0
    for visual_path in visuals_root.glob("**/visuals/*/visual.json"):
        payload = json.loads(visual_path.read_text(encoding="utf-8"))
        rebind_visual(payload, page)
        write_json(visual_path, payload)
        updated += 1
    return updated
