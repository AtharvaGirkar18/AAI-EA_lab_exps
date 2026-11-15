"""Public calculator API used by the demo app and MCP analysis exercises."""

from arithmetic import add, divide, multiply, subtract


def calculate_square(value: float) -> float:
    """Return the square of a numeric value."""
    return value * value


def calculate_average(values: list[float]) -> float:
    """Return the arithmetic mean; raise ValueError for an empty list."""
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)


__all__ = ["add", "subtract", "multiply", "divide", "calculate_square", "calculate_average"]
