"""Run identical fail-closed engineering gates locally and in CI."""

from __future__ import annotations

import os

# Subprocess calls use fixed argv without shell execution.
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    os.chdir(ROOT)
    Path("artifacts").mkdir(exist_ok=True)
    commands = [
        ["scripts/gates.py"],
        ["-m", "ruff", "format", "--check", "."],
        ["-m", "ruff", "check", "."],
        ["-m", "mypy", "src", "scripts"],
        [
            "-m",
            "pytest",
            "--cov=business_app",
            "--cov-branch",
            "--cov-report=term-missing",
            "--cov-report=xml:artifacts/coverage.xml",
            "--junitxml=artifacts/tests.xml",
        ],
        ["-m", "bandit", "-r", "src", "scripts", "-f", "json", "-o", "artifacts/bandit.json"],
        [
            "-m",
            "pip_audit",
            "-r",
            "requirements-dev.lock",
            "--require-hashes",
            "--disable-pip",
            "--format=json",
            "--output=artifacts/audit.json",
        ],
    ]
    for command in commands:
        print("GATE:", " ".join(command), flush=True)
        result = subprocess.run([sys.executable, *command], check=False)  # nosec B603
        if result.returncode:
            return result.returncode
    print("All engineering gates passed. Production readiness is a separate decision.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
