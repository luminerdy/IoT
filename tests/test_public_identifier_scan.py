import json

from scripts.check_public_identifiers import load_baseline, scan, write_baseline


def test_identifier_baseline_contains_hashes_not_matched_values(tmp_path):
    source = tmp_path / "example.txt"
    source.write_text("broker=192.168.42.9\n", encoding="utf-8")
    findings = scan([source])
    baseline = tmp_path / "baseline.json"

    write_baseline(findings, baseline)

    content = baseline.read_text(encoding="utf-8")
    assert len(findings) == 1
    assert "192.168.42.9" not in content
    assert findings[0].fingerprint in load_baseline(baseline)
    assert json.loads(content)["formatVersion"] == 1


def test_identifier_scan_reports_kind_without_exposing_match(tmp_path):
    source = tmp_path / "example.txt"
    source.write_text("device esp32-123456abcdef\n", encoding="utf-8")

    findings = scan([source])

    assert [(finding.kind, finding.line) for finding in findings] == [("device-id", 1)]
    assert "123456abcdef" not in repr(findings[0])
