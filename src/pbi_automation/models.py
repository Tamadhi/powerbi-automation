from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

NS = uuid.UUID("a3c1e9d0-4b7f-4d2a-9c11-7e2f0b1a4c5d")


def stable_guid(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def visual_name(*parts: str) -> str:
    return uuid.uuid5(NS, "|".join(("visual", *parts))).hex[:20]


@dataclass(frozen=True)
class FieldRef:
    table: str
    name: str
    kind: str  # column | measure

    @property
    def query_ref(self) -> str:
        return f"{self.table}.{self.name}"

    @classmethod
    def parse(cls, raw: str, *, kind: str | None = None) -> FieldRef:
        table, name = raw.split(".", 1)
        inferred = kind or ("measure" if name in MEASURE_NAMES else "column")
        return cls(table=table, name=name, kind=inferred)


MEASURE_NAMES = frozenset({"Total Sales", "Order Count", "Avg Order Value"})


@dataclass
class ChartSpec:
    visual: str
    x: FieldRef
    y: FieldRef


@dataclass
class PageSpec:
    key: str
    title: str
    cards: list[FieldRef]
    chart: ChartSpec
    table: list[FieldRef]
    slicer: FieldRef


@dataclass
class SourceSpec:
    type: str
    url: str


@dataclass
class DashboardSpec:
    name: str
    theme: Path
    template: Path | None
    source: SourceSpec
    pages: list[PageSpec]
    config_path: Path
    repo_root: Path

    @property
    def semantic_model_dir_name(self) -> str:
        return f"{self.name}.SemanticModel"

    @property
    def report_dir_name(self) -> str:
        return f"{self.name}.Report"


def load_spec(config_path: Path, repo_root: Path) -> DashboardSpec:
    raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = SourceSpec(type=raw["source"]["type"], url=raw["source"]["url"].rstrip("/"))
    theme = Path(raw["theme"])
    if not theme.is_absolute():
        theme = repo_root / theme
    template_raw = raw.get("template")
    template = None
    if template_raw:
        template = Path(template_raw)
        if not template.is_absolute():
            template = repo_root / template

    pages: list[PageSpec] = []
    for key, page in raw["pages"].items():
        chart = page["chart"]
        pages.append(
            PageSpec(
                key=key,
                title=page.get("title", key.title()),
                cards=[FieldRef.parse(item, kind="measure") for item in page["cards"]],
                chart=ChartSpec(
                    visual=chart.get("visual", "clusteredBarChart"),
                    x=FieldRef.parse(chart["x"], kind="column"),
                    y=FieldRef.parse(chart["y"], kind="measure"),
                ),
                table=[FieldRef.parse(item) for item in page["table"]],
                slicer=FieldRef.parse(page["slicer"], kind="column"),
            )
        )

    return DashboardSpec(
        name=raw["name"],
        theme=theme,
        template=template,
        source=source,
        pages=pages,
        config_path=config_path,
        repo_root=repo_root,
    )
