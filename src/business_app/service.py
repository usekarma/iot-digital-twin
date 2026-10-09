"""Example pure business service."""

from __future__ import annotations

from business_app.domain import WorkRequest


def calculate_result(request: WorkRequest) -> int:
    """Return an intentionally simple result used to verify project wiring."""
    return request.value * 2
