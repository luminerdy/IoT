from iot_home.dashboard import page


def test_dashboard_page_keeps_attic_and_thermal_sorting_contract() -> None:
    html = page().decode("utf-8")

    assert 'key: "attic"' in html
    assert 'label: "Attic"' in html
    assert "!isAtticGraphLocation(location)" in html
    assert 'zone?.type === "attic"' in html
    assert "deviceLabel(a).localeCompare(deviceLabel(b)" in html
    assert "return bTemp - aTemp || deviceLabel(a).localeCompare(deviceLabel(b));" in html
    assert "Math.min(75," in html
    assert "Math.max(100," in html
    assert "[max, 100, 75, min]" in html
