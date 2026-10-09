from __future__ import annotations

import pytest

from business_app.domain import WorkRequest
from business_app.service import calculate_result


def test_calculate_result() -> None:
    assert calculate_result(WorkRequest("req-1", 21)) == 42


@pytest.mark.parametrize("value, expected", [(0, 0), (1_000_000, 2_000_000)])
def test_boundaries(value: int, expected: int) -> None:
    assert calculate_result(WorkRequest("x" * 128, value)) == expected


@pytest.mark.parametrize("identifier", ["", " ", "x" * 129])
def test_invalid_identifiers(identifier: str) -> None:
    with pytest.raises(ValueError, match="request_id"):
        WorkRequest(identifier, 1)


@pytest.mark.parametrize("value", [-1, 1_000_001])
def test_invalid_values(value: int) -> None:
    with pytest.raises(ValueError, match="value"):
        WorkRequest("req-1", value)


@pytest.mark.parametrize(
    "identifier,value", [(None, 1), (1, 1), ("r", True), ("r", "1"), ("r", 1.0)]
)
def test_invalid_types(identifier: object, value: object) -> None:
    with pytest.raises(TypeError):
        WorkRequest(identifier, value)  # type: ignore[arg-type]


def test_deterministic_without_mutation() -> None:
    request = WorkRequest("req-1", 21)
    assert [calculate_result(request) for _ in range(3)] == [42, 42, 42]
    assert request == WorkRequest("req-1", 21)
