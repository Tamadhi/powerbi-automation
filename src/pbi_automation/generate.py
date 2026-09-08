from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pbi_automation.models import DashboardSpec, load_spec
from pbi_automation.pbir import write_report
from pbi_automation.tmdl import write_semantic_model


@dataclass
class GenerateResult:
    spec: DashboardSpec
    output_dir: Path
    model_dir: Path
    report_dir: Path
    pbip_path: Path


def generate(
    repo_root: Path,
    config_path: Path,
    output_dir: Path,
    template: Path | None = None,
) -> GenerateResult:
    spec = load_spec(config_path, repo_root)
    if template:
        spec.template = template if template.is_absolute() else repo_root / template
    if spec.source.type != "odata":
        raise ValueError(f"Unsupported source type: {spec.source.type}")
    model_dir = write_semantic_model(output_dir, spec)
    report_dir = write_report(output_dir, spec)
    return GenerateResult(
        spec=spec,
        output_dir=output_dir,
        model_dir=model_dir,
        report_dir=report_dir,
        pbip_path=output_dir / f"{spec.name}.pbip",
    )
