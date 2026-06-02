"""Money helpers. All amounts are integer paise (100 paise = 1 rupee); never floats."""

from decimal import Decimal, InvalidOperation


def to_paise(value: str | int) -> int:
    """Convert a rupee amount such as "499.50" or 499 to paise."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("amount must be a string or an integer number of rupees")
    try:
        rupees = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {value!r}") from exc
    if not rupees.is_finite():
        raise ValueError(f"not a finite number: {value!r}")
    if rupees.as_tuple().exponent < -2:
        raise ValueError("amount can have at most two decimal places")
    if rupees < 0:
        raise ValueError("amount cannot be negative")
    return int(rupees * 100)


def format_inr(paise: int) -> str:
    """Format paise for display, e.g. 123450 -> '₹1,234.50'."""
    sign = "-" if paise < 0 else ""
    rupees, remainder = divmod(abs(paise), 100)
    return f"{sign}₹{rupees:,}.{remainder:02d}"
