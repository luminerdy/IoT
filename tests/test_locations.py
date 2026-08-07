import json

import pytest
from iot_home.locations import load_locations, mapped_location, save_locations


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


def test_save_locations_sorts_and_strips_values(tmp_path):
    path = tmp_path / "config" / "locations.json"
    save_locations({" esp32-two ": " Garage ", "esp32-one": "Kitchen", "esp32-empty": ""}, path)

    assert load_locations(path) == {"esp32-one": "Kitchen", "esp32-two": "Garage"}
    assert list(json.loads(path.read_text(encoding="utf-8"))) == ["esp32-one", "esp32-two"]


def test_save_locations_rejects_non_string_mapping(tmp_path):
    with pytest.raises(ValueError, match="string device IDs"):
        save_locations({"esp32-one": 123}, tmp_path / "locations.json")
