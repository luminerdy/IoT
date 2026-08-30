from __future__ import annotations

import json
from pathlib import Path

DEFAULT_RETIRED_DEVICES_PATH = Path("config/retired_devices.json")


def load_retired_devices(path: Path | str = DEFAULT_RETIRED_DEVICES_PATH) -> set[str]:
    retired_path = Path(path)
    if not retired_path.exists():
        return set()

    with retired_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if isinstance(raw, list):
        devices = raw
    elif isinstance(raw, dict):
        devices = raw.get("devices")
    else:
        raise ValueError(f"{retired_path} must contain a JSON array or object")

    if not isinstance(devices, list):
        raise ValueError(f"{retired_path} must define a devices array")

    retired: set[str] = set()
    for device_id in devices:
        if not isinstance(device_id, str):
            raise ValueError(f"{retired_path} devices must be strings")
        clean_device_id = device_id.strip()
        if clean_device_id:
            retired.add(clean_device_id)
    return retired
