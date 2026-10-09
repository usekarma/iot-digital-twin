from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "gates", Path(__file__).resolve().parents[1] / "scripts/gates.py"
)
assert spec and spec.loader
gates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gates)


def write_spec(root: Path, tests: list[str], duplicate: bool = False) -> None:
    (root / "specs").mkdir()
    (root / "specs/example.md").write_text("AC-001: contract")
    criterion = {"id": "AC-001", "spec": "specs/example.md", "tests": tests}
    data = {"schema_version": 1, "criteria": [criterion] * (2 if duplicate else 1)}
    (root / "specs/acceptance.json").write_text(json.dumps(data))


def test_spec_maps_parameterized_test(tmp_path: Path) -> None:
    write_spec(tmp_path, ["tests/test_x.py::test_boundary"])
    gates.validate_specs(tmp_path, {"tests/test_x.py::test_boundary[0]"})


def test_missing_test_blocks_gate(tmp_path: Path) -> None:
    write_spec(tmp_path, ["tests/test_x.py::test_missing"])
    with pytest.raises(ValueError, match="Uncollected"):
        gates.validate_specs(tmp_path, {"tests/test_x.py::test_other"})


def test_duplicate_id_blocks_gate(tmp_path: Path) -> None:
    write_spec(tmp_path, ["tests/test_x.py::test_ok"], duplicate=True)
    with pytest.raises(ValueError, match="Duplicate"):
        gates.validate_specs(tmp_path, {"tests/test_x.py::test_ok"})


def test_path_escape_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="within"):
        gates.safe_file(tmp_path, "../outside.md")


def test_secret_is_rejected_without_printing_value(tmp_path: Path) -> None:
    credential = "AK" + "IA" + "A" * 16
    (tmp_path / "bad.txt").write_text(credential)
    with pytest.raises(ValueError, match="value withheld") as error:
        gates.scan_secrets(tmp_path, ["bad.txt"])
    assert credential not in str(error.value)


def write_readiness(root: Path, stage: str = "production") -> None:
    (root / "docs").mkdir()
    (root / "docs/evidence.md").write_text(
        "## Evidence\nSynthetic drill succeeded with expected output and owner review.\n"
        "## Limitations\nSynthetic test does not demonstrate real production release approval.\n"
    )
    checks = {
        key: {"status": "passed", "owner": "Test owner", "evidence": "docs/evidence.md"}
        for key in gates.READINESS_KEYS
    }
    (root / "docs/readiness.json").write_text(
        json.dumps({"schema_version": 1, "stage": stage, "checks": checks})
    )


def test_prototype_cannot_pass_production(tmp_path: Path) -> None:
    write_readiness(tmp_path, "prototype")
    with pytest.raises(ValueError, match="stage"):
        gates.validate_readiness(tmp_path)


def test_readiness_requires_evidence_and_owner(tmp_path: Path) -> None:
    write_readiness(tmp_path)
    gates.validate_readiness(tmp_path)
    path = tmp_path / "docs/readiness.json"
    data = json.loads(path.read_text())
    data["checks"]["security_review"]["owner"] = ""
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="owner"):
        gates.validate_readiness(tmp_path)


def test_placeholder_evidence_is_rejected(tmp_path: Path) -> None:
    write_readiness(tmp_path)
    (tmp_path / "docs/evidence.md").write_text(
        "## Evidence\nTODO replace this long placeholder with an actual performed verification.\n"
        "## Limitations\nExample has no production evidence or approval; release remains blocked.\n"
    )
    with pytest.raises(ValueError, match="placeholder"):
        gates.validate_readiness(tmp_path)
