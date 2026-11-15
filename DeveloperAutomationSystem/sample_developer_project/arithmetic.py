"""Core arithmetic operations."""


def add(left: float, right: float) -> float:
    """Add two numbers."""
    return left + right


def subtract(left: float, right: float) -> float:
    """Subtract right from left."""
    return left - right


def multiply(left: float, right: float) -> float:
    """Multiply two numbers."""
    return left * right


def divide(left: float, right: float) -> float:
    """Divide left by right, rejecting a zero divisor."""
    if right == 0:
        raise ZeroDivisionError("division by zero")
    return left / right
