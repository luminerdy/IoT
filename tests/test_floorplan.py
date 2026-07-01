import json

import pytest

from iot_home.floorplan import load_floorplan


def test_load_floorplan_returns_empty_default_for_missing_file(tmp_path):
    assert load_floorplan(tmp_path / "missing.json") == {"backgroundImage": None, "zones": []}


def test_load_floorplan_normalizes_valid_zones(tmp_path):
    path = tmp_path / "floorplan.json"
    path.write_text(
        json.dumps(
            {
                "backgroundImage": "/dashboard-assets/house.png",
                "zones": [
                    {"location": "Kitchen", "x": 10, "y": 20, "w": 30, "h": 40, "type": "utility"}
                ],
            }
        ),
        encoding="utf-8",
    )

    assert load_floorplan(path) == {
        "backgroundImage": "/dashboard-assets/house.png",
        "zones": [{"location": "Kitchen", "x": 10.0, "y": 20.0, "w": 30.0, "h": 40.0, "type": "utility"}],
    }


@pytest.mark.parametrize(
    "payload, message",
    [
        ([], "must contain a JSON object"),
        ({"zones": "bad"}, "zones must be a list"),
        ({"zones": [{"location": "", "x": 1, "y": 1, "w": 1, "h": 1}]}, "location must be"),
        ({"zones": [{"location": "Kitchen", "x": True, "y": 1, "w": 1, "h": 1}]}, "x must be a number"),
    ],
)
def test_load_floorplan_rejects_invalid_shapes(tmp_path, payload, message):
    path = tmp_path / "floorplan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_floorplan(path)
