"""Validated domain input for the worked example contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkRequest:
    """A bounded request with no external side effects."""

    request_id: str
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not self.request_id.strip() or len(self.request_id) > 128:
            raise ValueError("request_id must be nonblank and at most 128 characters")
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise TypeError("value must be an integer, not bool")
        if not 0 <= self.value <= 1_000_000:
            raise ValueError("value must be between 0 and 1000000")
