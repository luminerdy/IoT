from __future__ import annotations

import json
from numbers import Real
from pathlib import Path


DEFAULT_FLOORPLAN_PATH = Path("config/floorplan.json")


def load_floorplan(path: Path | str = DEFAULT_FLOORPLAN_PATH) -> dict:
    floorplan_path = Path(path)
    if not floorplan_path.exists():
        return {"backgroundImage": None, "zones": []}

    with floorplan_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"{floorplan_path} must contain a JSON object")

    background_image = raw.get("backgroundImage")
    if background_image is not None and not isinstance(background_image, str):
        raise ValueError(f"{floorplan_path} backgroundImage must be a string or null")

    zones_raw = raw.get("zones", [])
    if not isinstance(zones_raw, list):
        raise ValueError(f"{floorplan_path} zones must be a list")

    zones = []
    for index, zone in enumerate(zones_raw):
        if not isinstance(zone, dict):
            raise ValueError(f"{floorplan_path} zones[{index}] must be an object")
        location = zone.get("location")
        if not isinstance(location, str) or not location:
            raise ValueError(f"{floorplan_path} zones[{index}].location must be a non-empty string")

        normalized = {"location": location}
        for key in ("x", "y", "w", "h"):
            value = zone.get(key)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"{floorplan_path} zones[{index}].{key} must be a number")
            normalized[key] = float(value)

        zone_type = zone.get("type")
        if zone_type is not None:
            if not isinstance(zone_type, str):
                raise ValueError(f"{floorplan_path} zones[{index}].type must be a string")
            normalized["type"] = zone_type

        zones.append(normalized)

    return {"backgroundImage": background_image, "zones": zones}
