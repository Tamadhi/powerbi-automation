from __future__ import annotations

from pathlib import Path
from shutil import copytree, ignore_patterns
from typing import Any

from pbi_automation.io_util import copy_file, write_json
from pbi_automation.models import DashboardSpec, FieldRef, visual_name
from pbi_automation.platform import write_platform
from pbi_automation.rebind import rebind_report, resolve_template

VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.4.0/schema.json"
)
PAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json"
)
PAGES_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/pagesMetadata/1.0.0/schema.json"
)
REPORT_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/2.0.0/schema.json"
)
VERSION_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/versionMetadata/1.0.0/schema.json"
)
PBIR_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definitionProperties/2.0.0/schema.json"
)
PBIP_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json"

THEME_VERSIONS = {"visual": "2.6.0", "report": "3.1.0", "page": "2.3.0"}


def _field_expr(ref: FieldRef) -> dict[str, Any]:
    kind = "Measure" if ref.kind == "measure" else "Column"
    return {
        kind: {
            "Expression": {"SourceRef": {"Entity": ref.table}},
            "Property": ref.name,
        }
    }


def _projection(ref: FieldRef, *, active: bool | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "field": _field_expr(ref),
        "queryRef": ref.query_ref,
        "nativeQueryRef": ref.name,
    }
    if active is not None:
        payload["active"] = active
    return payload


def _container_objects(*, show_title: bool, title: str | None = None) -> dict[str, Any]:
    title_props: dict[str, Any] = {"show": {"expr": {"Literal": {"Value": "true" if show_title else "false"}}}}
    if title:
        title_props["text"] = {"expr": {"Literal": {"Value": f"'{title}'"}}}
    return {
        "background": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
        "border": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
        "dropShadow": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
        "title": [{"properties": title_props}],
    }


def _visual(
    *,
    name: str,
    visual_type: str,
    position: dict[str, float | int],
    query_state: dict[str, Any],
    objects: dict[str, Any] | None = None,
    sort: FieldRef | None = None,
    show_title: bool = False,
    title: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {"queryState": query_state}
    if sort:
        query["sortDefinition"] = {
            "sort": [{"field": _field_expr(sort), "direction": "Descending"}]
        }
    visual: dict[str, Any] = {
        "visualType": visual_type,
        "query": query,
        "visualContainerObjects": _container_objects(show_title=show_title, title=title),
    }
    if objects:
        visual["objects"] = objects
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": position,
        "visual": visual,
    }


def _textbox(name: str, text: str, position: dict[str, float | int]) -> dict[str, Any]:
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": position,
        "visual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "value": text,
                                            "textStyle": {
                                                "fontFamily": "Segoe UI",
                                                "fontSize": "20pt",
                                                "fontWeight": "bold",
                                                "color": "#0F2C4C",
                                            },
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            },
        },
    }


def _write_visual(page_dir: Path, payload: dict[str, Any]) -> None:
    visual_dir = page_dir / "visuals" / payload["name"]
    write_json(visual_dir / "visual.json", payload)


def _apply_theme(report_json: dict[str, Any], theme_file_name: str) -> dict[str, Any]:
    report_json.setdefault("themeCollection", {})
    report_json["themeCollection"]["baseTheme"] = {
        "name": "CY24SU10",
        "reportVersionAtImport": THEME_VERSIONS,
        "type": "SharedResources",
    }
    report_json["themeCollection"]["customTheme"] = {
        "name": theme_file_name,
        "reportVersionAtImport": THEME_VERSIONS,
        "type": "RegisteredResources",
    }
    packages = list(report_json.get("resourcePackages") or [])
    packages = [pkg for pkg in packages if pkg.get("name") != "RegisteredResources"]
    packages.append(
        {
            "name": "RegisteredResources",
            "type": "RegisteredResources",
            "items": [
                {
                    "name": theme_file_name,
                    "path": theme_file_name,
                    "type": "CustomTheme",
                }
            ],
        }
    )
    report_json["resourcePackages"] = packages
    return report_json


def _builtin_report(spec: DashboardSpec, report_dir: Path, theme_file_name: str) -> None:
    page = first_page(spec)
    page_name = visual_name(spec.name, page.key, "page")
    definition = report_dir / "definition"
    page_dir = definition / "pages" / page_name

    write_json(
        definition / "version.json",
        {"$schema": VERSION_SCHEMA, "version": "2.0.0"},
    )
    write_json(
        definition / "report.json",
        _apply_theme(
            {
                "$schema": REPORT_SCHEMA,
                "themeCollection": {},
                "objects": {
                    "section": [
                        {
                            "properties": {
                                "verticalAlign": {"expr": {"Literal": {"Value": "'Top'"}}}
                            }
                        }
                    ]
                },
                "settings": {
                    "useStylableVisualContainerHeader": True,
                    "defaultDrillFilterOtherVisuals": True,
                },
            },
            theme_file_name,
        ),
    )
    write_json(
        definition / "pages" / "pages.json",
        {
            "$schema": PAGES_SCHEMA,
            "pageOrder": [page_name],
            "activePageName": page_name,
        },
    )
    write_json(
        page_dir / "page.json",
        {
            "$schema": PAGE_SCHEMA,
            "name": page_name,
            "displayName": page.title,
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
            "objects": {
                "background": [
                    {
                        "properties": {
                            "color": {
                                "solid": {
                                    "color": {"expr": {"Literal": {"Value": "'#F4F7FA'"}}}
                                }
                            },
                            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
                        }
                    }
                ]
            },
        },
    )

    _write_visual(
        page_dir,
        _textbox(
            visual_name(spec.name, page.key, "title"),
            page.title,
            {"x": 24, "y": 16, "z": 0, "height": 48, "width": 700, "tabOrder": 0},
        ),
    )
    _write_visual(
        page_dir,
        _visual(
            name=visual_name(spec.name, page.key, "kpis"),
            visual_type="cardVisual",
            position={"x": 24, "y": 72, "z": 1000, "height": 120, "width": 1232, "tabOrder": 1000},
            query_state={"Data": {"projections": [_projection(card) for card in page.cards]}},
            show_title=False,
        ),
    )
    _write_visual(
        page_dir,
        _visual(
            name=visual_name(spec.name, page.key, "slicer"),
            visual_type="slicer",
            position={"x": 24, "y": 208, "z": 2000, "height": 88, "width": 280, "tabOrder": 2000},
            query_state={"Values": {"projections": [_projection(page.slicer)]}},
            objects={
                "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
                "header": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{page.slicer.name}'"}}},
                        }
                    }
                ],
            },
            show_title=False,
        ),
    )
    _write_visual(
        page_dir,
        _visual(
            name=visual_name(spec.name, page.key, "chart"),
            visual_type=page.chart.visual,
            position={"x": 24, "y": 312, "z": 3000, "height": 384, "width": 620, "tabOrder": 3000},
            query_state={
                "Category": {"projections": [_projection(page.chart.x, active=True)]},
                "Y": {"projections": [_projection(page.chart.y)]},
            },
            sort=page.chart.y,
            objects={
                "categoryAxis": [
                    {
                        "properties": {
                            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                        }
                    }
                ],
                "valueAxis": [
                    {
                        "properties": {
                            "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                        }
                    }
                ],
                "labels": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "labelPrecision": {"expr": {"Literal": {"Value": "0L"}}},
                        }
                    }
                ],
            },
            show_title=True,
            title=f"{page.chart.y.name} by {page.chart.x.name}",
        ),
    )
    _write_visual(
        page_dir,
        _visual(
            name=visual_name(spec.name, page.key, "table"),
            visual_type="tableEx",
            position={"x": 660, "y": 312, "z": 4000, "height": 384, "width": 596, "tabOrder": 4000},
            query_state={"Values": {"projections": [_projection(col) for col in page.table]}},
            objects={
                "columnHeaders": [
                    {
                        "properties": {
                            "autoSizeColumnWidth": {"expr": {"Literal": {"Value": "true"}}}
                        }
                    }
                ]
            },
            show_title=True,
            title="Orders",
        ),
    )


def _copy_template(template: Path, report_dir: Path, spec: DashboardSpec, theme_file_name: str) -> None:
    source = resolve_template(template)
    copytree(
        source,
        report_dir,
        dirs_exist_ok=True,
        ignore=ignore_patterns(".platform", "definition.pbir"),
    )
    report_json_path = report_dir / "definition" / "report.json"
    if report_json_path.exists():
        import json

        report_json = json.loads(report_json_path.read_text(encoding="utf-8"))
        write_json(report_json_path, _apply_theme(report_json, theme_file_name))
    rebind_report(report_dir, spec)


def write_report(output_dir: Path, spec: DashboardSpec) -> Path:
    report_dir = output_dir / spec.report_dir_name
    theme_file_name = spec.theme.name
    write_platform(
        report_dir,
        item_type="Report",
        display_name=spec.name,
        description=f"{spec.name} report generated from template",
    )
    write_json(
        report_dir / "definition.pbir",
        {
            "$schema": PBIR_SCHEMA,
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{spec.semantic_model_dir_name}"}},
        },
    )
    if spec.template and spec.template.exists():
        _copy_template(spec.template, report_dir, spec, theme_file_name)
    else:
        _builtin_report(spec, report_dir, theme_file_name)

    if spec.theme.exists():
        copy_file(
            spec.theme,
            report_dir / "StaticResources" / "RegisteredResources" / theme_file_name,
        )
    write_json(
        output_dir / f"{spec.name}.pbip",
        {
            "$schema": PBIP_SCHEMA,
            "version": "1.0",
            "artifacts": [{"report": {"path": spec.report_dir_name}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    return report_dir
