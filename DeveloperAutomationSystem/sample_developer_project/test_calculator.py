import pytest

from arithmetic import add, divide, multiply, subtract
from calculator import calculate_average, calculate_square
from app import summarize


@pytest.mark.parametrize("left,right,expected", [(1, 2, 3), (0, 0, 0), (-4, 9, 5), (1.5, 2.5, 4)])
def test_add(left, right, expected):
    assert add(left, right) == expected


@pytest.mark.parametrize("left,right,expected", [(5, 2, 3), (0, 0, 0), (-4, -9, 5), (1.5, .5, 1)])
def test_subtract(left, right, expected):
    assert subtract(left, right) == expected


@pytest.mark.parametrize("left,right,expected", [(3, 2, 6), (0, 9, 0), (-4, 3, -12), (1.5, 2, 3)])
def test_multiply(left, right, expected):
    assert multiply(left, right) == expected


@pytest.mark.parametrize("left,right,expected", [(6, 2, 3), (0, 4, 0), (-9, 3, -3), (1, 4, .25)])
def test_divide(left, right, expected):
    assert divide(left, right) == expected


def test_divide_by_zero_is_rejected():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)


@pytest.mark.parametrize("value,expected", [(0, 0), (3, 9), (-4, 16), (1.5, 2.25)])
def test_square(value, expected):
    assert calculate_square(value) == expected


def test_average():
    assert calculate_average([2, 4, 6]) == 4


def test_average_empty_is_rejected():
    with pytest.raises(ValueError):
        calculate_average([])


def test_summarize():
    result = summarize([2, 4, 6])
    assert result["total"] == 12
    assert result["average"] == 4
    assert result["first_square"] == 4


def test_summarize_empty_is_rejected():
    with pytest.raises(ValueError):
        summarize([])
