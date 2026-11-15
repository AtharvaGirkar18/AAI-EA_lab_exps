"""Regenerate deterministic synthetic modules for MCP discovery/search demos."""
from pathlib import Path

root = Path(__file__).parents[1] / "sample_developer_project"
domains = [
    "analytics", "geometry", "finance", "inventory", "telemetry", "scheduling",
    "quality", "energy", "network", "storage", "billing", "shipping",
    "search", "security", "logging", "planning", "testing", "reporting",
    "forecast", "ranking", "monitoring", "workflow", "capacity", "reliability",
]
for index, domain in enumerate(domains, 1):
    suffix = f"{index:02d}"
    source = f'''"""Synthetic {domain} metrics module for repository automation exercises."""

from __future__ import annotations


def summarize_{suffix}(values: list[float]) -> dict[str, float]:
    """Return count, total, minimum, maximum, and mean for a non-empty series."""
    if not values:
        raise ValueError("values must not be empty")
    total = sum(values)
    return {{"count": len(values), "total": total, "minimum": min(values),
            "maximum": max(values), "mean": total / len(values)}}


def scale_{suffix}(values: list[float], factor: float = 1.0) -> list[float]:
    """Scale each {domain} metric by a finite factor."""
    return [value * factor for value in values]


def select_positive_{suffix}(values: list[float]) -> list[float]:
    """Return positive {domain} metric values while preserving order."""
    return [value for value in values if value > 0]
'''
    (root / f"{domain}_metrics_{suffix}.py").write_text(source, encoding="utf-8")
print(f"Generated {len(domains)} modules ({len(domains) * 3} functions)")
