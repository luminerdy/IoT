#!/usr/bin/env python3
"""Reject local identifiers not recorded in the hash-only baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

BASELINE_PATH = Path("config/public-identifier-baseline.json")
SCAN_EXCLUDES = {BASELINE_PATH, Path("scripts/check_public_identifiers.py")}
LOCAL_ONLY_EXCLUDES = {Path("AGENTS.md"), Path("IoT-code-review.md")}
PATTERNS = {
    "private-ipv4": re.compile(
        rb"(?<![0-9])(?:10(?:\.[0-9]{1,3}){3}|192\.168(?:\.[0-9]{1,3}){2}|"
        rb"172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2})(?![0-9])"
    ),
    "mac-address": re.compile(rb"(?i)(?<![0-9a-f])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f])"),
    "device-id": re.compile(rb"(?i)\besp32-[0-9a-f]{12}\b"),
    "local-hostname": re.compile(rb"(?i)\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local\b"),
    "installed-hostname": re.compile(rb"\bPiServer\b"),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    fingerprint: str


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    return [
        path
        for item in output.split(b"\0")
        if item and (path := Path(item.decode())) not in LOCAL_ONLY_EXCLUDES
    ]


def fingerprint(path: Path, kind: str, value: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(path.as_posix().encode())
    digest.update(b"\0")
    digest.update(kind.encode())
    digest.update(b"\0")
    digest.update(value.lower())
    return digest.hexdigest()


def scan(paths: list[Path]) -> list[Finding]:
    findings: dict[str, Finding] = {}
    for path in paths:
        if path in SCAN_EXCLUDES or not path.is_file():
            continue
        try:
            content = path.read_bytes()
        except OSError:
            continue
        if b"\0" in content:
            continue
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                value = match.group(0)
                item_fingerprint = fingerprint(path, kind, value)
                findings[item_fingerprint] = Finding(
                    path=path.as_posix(),
                    line=content.count(b"\n", 0, match.start()) + 1,
                    kind=kind,
                    fingerprint=item_fingerprint,
                )
    return sorted(findings.values(), key=lambda item: (item.path, item.line, item.kind))


def load_baseline(path: Path = BASELINE_PATH) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("formatVersion") != 1 or not isinstance(data.get("fingerprints"), list):
        raise ValueError(f"invalid identifier baseline: {path}")
    return {str(value) for value in data["fingerprints"]}


def write_baseline(findings: list[Finding], path: Path = BASELINE_PATH) -> None:
    payload = {
        "formatVersion": 1,
        "description": "Accepted pre-scan identifier fingerprints; matched values are not stored.",
        "fingerprints": sorted(finding.fingerprint for finding in findings),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Explicitly accept current findings by replacing the hash-only baseline.",
    )
    args = parser.parse_args()
    findings = scan(tracked_files())
    if args.write_baseline:
        write_baseline(findings)
        print(f"Wrote {len(findings)} accepted identifier fingerprints to {BASELINE_PATH}")
        return 0

    try:
        baseline = load_baseline()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Identifier scan failed: {exc}")
        return 2
    unexpected = [finding for finding in findings if finding.fingerprint not in baseline]
    stale = baseline - {finding.fingerprint for finding in findings}
    if unexpected:
        print("New local identifier findings (matched values redacted):")
        for finding in unexpected:
            print(f"  {finding.path}:{finding.line}: {finding.kind}")
        print("Sanitize these values. Baseline changes require an explicit security decision.")
        return 1
    print(
        f"Identifier scan passed: {len(findings)} accepted fingerprints, "
        f"{len(stale)} stale baseline fingerprints"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
