"""Independently compare a saved SiteWise API response against a run manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def verify(manifest: dict[str, Any], history: dict[str, Any]) -> int:
    """Fail closed on dry runs, partial/paginated history, conflicts and bad quality."""
    if manifest.get("live_attempted") is not True:
        raise ValueError("dry-run manifests cannot establish cloud ingestion")
    packets = manifest.get("observations")
    if not isinstance(packets, list) or len(packets) != 20 or history.get("nextToken"):
        raise ValueError("exact twenty-point manifest and complete history required")
    expected = {}
    for p in packets:
        key = (p["event_time_seconds"], p["event_time_nanos"])
        if key in expected or type(p["severity"]) is not int:
            raise ValueError("invalid manifest")
        expected[key] = p["severity"]
    seen = {}
    for point in history.get("assetPropertyValueHistory", []):
        key = (point["timestamp"]["timeInSeconds"], point["timestamp"].get("offsetInNanos", 0))
        value = point["value"].get("integerValue")
        if point["quality"] != "GOOD" or type(value) is not int or key in seen:
            raise ValueError("invalid/duplicate SiteWise point")
        seen[key] = value
    if seen != expected:
        raise ValueError("missing, unexpected or conflicting SiteWise values")
    return len(seen)


def main() -> None:
    """Read only local evidence; acquiring AWS history is a separate operator action."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    args = parser.parse_args()
    count = verify(json.loads(args.manifest.read_text()), json.loads(args.history.read_text()))
    print(f"{count} SiteWise timestamp/value pairs match; latency and identity evidence separate.")


if __name__ == "__main__":
    main()
