"""Synthetic shipping metrics module for repository automation exercises."""

from __future__ import annotations


def summarize_12(values: list[float]) -> dict[str, float]:
    """Return count, total, minimum, maximum, and mean for a non-empty series."""
    if not values:
        raise ValueError("values must not be empty")
    total = sum(values)
    return {"count": len(values), "total": total, "minimum": min(values),
            "maximum": max(values), "mean": total / len(values)}


def scale_12(values: list[float], factor: float = 1.0) -> list[float]:
    """Scale each shipping metric by a finite factor."""
    return [value * factor for value in values]


def select_positive_12(values: list[float]) -> list[float]:
    """Return positive shipping metric values while preserving order."""
    return [value for value in values if value > 0]
