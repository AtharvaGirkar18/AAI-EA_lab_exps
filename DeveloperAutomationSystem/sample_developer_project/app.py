"""Small command-line-style example that composes calculator operations."""

from calculator import add, calculate_average, calculate_square, divide, multiply, subtract


def summarize(values: list[float]) -> dict[str, float]:
    """Return useful summary calculations for a list of values."""
    if not values:
        raise ValueError("provide at least one value")
    total = sum(values)
    return {
        "total": total,
        "average": calculate_average(values),
        "first_square": calculate_square(values[0]),
        "difference": subtract(values[-1], values[0]),
        "product": multiply(values[0], values[-1]),
        "safe_ratio": divide(total, len(values)),
        "sum_check": add(values[0], values[-1]),
    }
