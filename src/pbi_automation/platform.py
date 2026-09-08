from __future__ import annotations

from pathlib import Path

from pbi_automation.io_util import write_json
from pbi_automation.models import stable_guid


PLATFORM_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/"
    "gitIntegration/platformProperties/2.0.0/schema.json"
)


def write_platform(item_dir: Path, *, item_type: str, display_name: str, description: str) -> None:
    payload = {
        "$schema": PLATFORM_SCHEMA,
        "metadata": {
            "type": item_type,
            "displayName": display_name,
            "description": description,
        },
        "config": {
            "version": "2.0",
            "logicalId": stable_guid("logical", item_type, display_name),
        },
    }
    write_json(item_dir / ".platform", payload)
