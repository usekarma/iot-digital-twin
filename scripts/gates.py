"""Validate spec traceability, selected secret patterns, and production evidence."""

from __future__ import annotations

import argparse
import json
import re
import shutil

# Subprocess calls use fixed argv without shell execution.
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
READINESS_KEYS = {
    "stakeholder_validation",
    "security_review",
    "slo_and_alerts",
    "rollback_drill",
    "recovery_drill",
    "capacity_and_cost",
    "release_approval",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
)


def safe_file(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if Path(value).is_absolute() or not candidate.is_relative_to(root.resolve()):
        raise ValueError("Evidence/spec path must stay within the repository")
    if not candidate.is_file():
        raise ValueError(f"Missing file: {value}")
    return candidate


def read_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError(f"Unsupported document schema: {path.name}")
    return data


def validate_specs(root: Path, collected: set[str]) -> None:
    data = read_object(root / "specs/acceptance.json")
    criteria = data.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("At least one acceptance criterion is required")
    seen: set[str] = set()
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise ValueError("Each criterion must be an object")
        identifier = criterion.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"AC-\d{3,}", identifier):
            raise ValueError("Invalid acceptance ID")
        if identifier in seen:
            raise ValueError(f"Duplicate acceptance ID: {identifier}")
        seen.add(identifier)
        spec = criterion.get("spec")
        if not isinstance(spec, str) or identifier not in safe_file(root, spec).read_text():
            raise ValueError(f"Missing spec reference for {identifier}")
        tests = criterion.get("tests")
        if not isinstance(tests, list) or not tests:
            raise ValueError(f"No tests mapped for {identifier}")
        for test in tests:
            if not isinstance(test, str) or not any(
                node == test or node.startswith(test + "[") for node in collected
            ):
                raise ValueError(f"Uncollected test for {identifier}: {test}")


def validate_readiness(root: Path) -> None:
    data = read_object(root / "docs/readiness.json")
    if data.get("stage") != "production":
        raise ValueError("Production blocked: stage is not production")
    checks = data.get("checks")
    if not isinstance(checks, dict) or set(checks) != READINESS_KEYS:
        raise ValueError("Production requires exactly the documented readiness checks")
    for name, entry in checks.items():
        if not isinstance(entry, dict) or entry.get("status") != "passed":
            raise ValueError(f"Production blocked: {name} is not passed")
        owner = entry.get("owner")
        evidence = entry.get("evidence")
        if not isinstance(owner, str) or not owner.strip() or owner.lower() in {"tbd", "todo"}:
            raise ValueError(f"Production blocked: {name} requires an owner")
        if not isinstance(evidence, str) or not evidence.endswith(".md"):
            raise ValueError(f"Production blocked: {name} requires Markdown evidence")
        text = safe_file(root, evidence).read_text()
        for heading in ("Evidence", "Limitations"):
            match = re.search(rf"^## {heading}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
            if not match or len(match[1].strip()) < 40:
                raise ValueError(f"Production blocked: {name} lacks substantive {heading}")
            if re.search(r"\b(?:TODO|TBD|PLACEHOLDER)\b", match[1], re.I):
                raise ValueError(f"Production blocked: {name} contains placeholder evidence")


def scan_secrets(root: Path, paths: list[str]) -> None:
    for name in paths:
        content = safe_file(root, name).read_bytes()
        if b"\0" in content:
            continue
        text = content.decode("utf-8", errors="replace")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            raise ValueError(f"Potential credential in {name}; value withheld")


def collect_tests(root: Path) -> set[str]:
    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-o", "addopts="],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError("Pytest collection failed: " + result.stdout + result.stderr)
    return {line.strip() for line in result.stdout.splitlines() if "::" in line}


def tracked_files(root: Path) -> list[str]:
    git = shutil.which("git")
    if git is None:
        raise ValueError("Git is required for the credential scan")
    # Fixed arguments; Git is resolved from the trusted development PATH.
    result = subprocess.run(  # nosec B603
        [git, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return sorted(set(result.stdout.decode().strip("\0").split("\0")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    try:
        validate_specs(ROOT, collect_tests(ROOT))
        scan_secrets(ROOT, tracked_files(ROOT))
        if args.production:
            validate_readiness(ROOT)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"GATE FAILED: {exc}", file=sys.stderr)
        return 1
    print("Specs and selected credential patterns passed.")
    if args.production:
        print("Readiness structure passed; human evidence review and release decision required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
