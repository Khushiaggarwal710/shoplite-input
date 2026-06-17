"""Money helpers."""

import pytest

from shoplite.utils.money import format_inr, to_paise


@pytest.mark.parametrize("value, expected", [("499", 49900), ("499.5", 49950),
                                             ("0.01", 1), (12, 1200)])
def test_to_paise(value, expected):
    """Rupee strings and ints convert exactly."""
    assert to_paise(value) == expected


@pytest.mark.parametrize("bad", ["1.234", "-5", "abc", "NaN", "Infinity", 1.5, True, None])
def test_to_paise_rejects_bad_input(bad):
    """Floats, booleans, negatives and non-numbers are rejected."""
    with pytest.raises(ValueError):
        to_paise(bad)


def test_format_inr():
    """Paise display as rupees with separators."""
    assert format_inr(123450) == "₹1,234.50"
    assert format_inr(-5) == "-₹0.05"
