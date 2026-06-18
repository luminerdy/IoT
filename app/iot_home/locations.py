from __future__ import annotations

import json
from pathlib import Path


DEFAULT_LOCATIONS_PATH = Path("config/locations.json")


def load_locations(path: Path | str = DEFAULT_LOCATIONS_PATH) -> dict[str, str]:
    location_path = Path(path)
    if not location_path.exists():
        return {}

    with location_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"{location_path} must contain a JSON object")

    locations: dict[str, str] = {}
    for device_id, location in raw.items():
        if not isinstance(device_id, str) or not isinstance(location, str):
            raise ValueError(f"{location_path} must map string device IDs to string locations")
        locations[device_id] = location
    return locations


def mapped_location(device_id: str, reported_location: str | None, locations: dict[str, str]) -> str:
    if device_id in locations:
        return locations[device_id]
    if reported_location and reported_location != "UNMAPPED":
        return reported_location
    return "UNMAPPED"
