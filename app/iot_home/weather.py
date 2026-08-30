from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlencode

WEATHER_METRIC = "internet_outdoor_temperature_f"


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def fetch_json(url: str, timeout: float = 5.0) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "iot-home-dashboard/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def geocode_weather_zip(weather_zip: str) -> tuple[float, float, str] | None:
    query = urlencode(
        {"name": f"{weather_zip}, US", "count": 1, "language": "en", "format": "json"}
    )
    data = fetch_json(f"https://geocoding-api.open-meteo.com/v1/search?{query}")
    results = data.get("results")
    if not isinstance(results, list) or not results:
        return None
    match = results[0]
    latitude = match.get("latitude")
    longitude = match.get("longitude")
    if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
        return None
    name_parts = [
        str(value)
        for value in (match.get("name"), match.get("admin1"), match.get("country_code"))
        if value
    ]
    return float(latitude), float(longitude), ", ".join(name_parts) or weather_zip


def resolve_weather_location(
    weather_zip: str | None, latitude: float | None, longitude: float | None
) -> tuple[float, float, str | None] | None:
    if latitude is not None and longitude is not None:
        return latitude, longitude, None
    if weather_zip:
        return geocode_weather_zip(weather_zip)
    return None


def fetch_weather_temperature_f(latitude: float, longitude: float) -> tuple[float, datetime]:
    query = urlencode(
        {
            "latitude": f"{latitude:.6f}",
            "longitude": f"{longitude:.6f}",
            "current": "temperature_2m",
            "temperature_unit": "fahrenheit",
            "timezone": "UTC",
        }
    )
    data = fetch_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    current = data.get("current")
    if not isinstance(current, dict):
        raise ValueError("weather response did not include current conditions")
    temperature = current.get("temperature_2m")
    sampled_at = parse_utc(current.get("time"))
    if not isinstance(temperature, int | float) or sampled_at is None:
        raise ValueError("weather response did not include a current temperature")
    return float(temperature), sampled_at
