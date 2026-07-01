import json

import pytest

from iot_home.locations import load_locations, mapped_location


def test_load_locations_returns_empty_for_missing_file(tmp_path):
    assert load_locations(tmp_path / "missing.json") == {}


def test_load_locations_validates_string_mapping(tmp_path):
    path = tmp_path / "locations.json"
    path.write_text(json.dumps({"esp32-one": "Kitchen"}), encoding="utf-8")

    assert load_locations(path) == {"esp32-one": "Kitchen"}


def test_load_locations_rejects_non_string_values(tmp_path):
    path = tmp_path / "locations.json"
    path.write_text(json.dumps({"esp32-one": 123}), encoding="utf-8")

    with pytest.raises(ValueError, match="string device IDs"):
        load_locations(path)


def test_mapped_location_prefers_local_mapping():
    assert mapped_location("esp32-one", "UNMAPPED", {"esp32-one": "Kitchen"}) == "Kitchen"
    assert mapped_location("esp32-two", "Garage", {}) == "Garage"
    assert mapped_location("esp32-three", "UNMAPPED", {}) == "UNMAPPED"
