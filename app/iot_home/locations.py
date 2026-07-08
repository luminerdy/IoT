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


def save_locations(locations: dict[str, str], path: Path | str = DEFAULT_LOCATIONS_PATH) -> None:
    location_path = Path(path)
    location_path.parent.mkdir(parents=True, exist_ok=True)

    normalized: dict[str, str] = {}
    for device_id, location in locations.items():
        if not isinstance(device_id, str) or not isinstance(location, str):
            raise ValueError("locations must map string device IDs to string locations")
        clean_device_id = device_id.strip()
        clean_location = location.strip()
        if clean_device_id and clean_location:
            normalized[clean_device_id] = clean_location

    tmp_path = location_path.with_name(f".{location_path.name}.tmp")
    tmp_path.write_text(
        json.dumps(dict(sorted(normalized.items())), indent=2) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(location_path)


def mapped_location(device_id: str, reported_location: str | None, locations: dict[str, str]) -> str:
    if device_id in locations:
        return locations[device_id]
    if reported_location and reported_location != "UNMAPPED":
        return reported_location
    return "UNMAPPED"
