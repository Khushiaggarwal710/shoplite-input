"""Turn bad request input into a 422 that names the field."""

from shoplite.errors import ValidationError


def require_object(payload: object) -> dict:
    """Check the request body is a JSON object."""
    if not isinstance(payload, dict):
        raise ValidationError("request body must be a JSON object")
    return payload


def get_str(payload: dict, name: str, *, required: bool = True, max_len: int = 255) -> str | None:
    """Read a trimmed string field."""
    value = payload.get(name)
    if value is None:
        if required:
            raise ValidationError(f"'{name}' is required", details={"field": name})
        return None
    if not isinstance(value, str):
        raise ValidationError(f"'{name}' must be a string", details={"field": name})
    value = value.strip()
    if required and not value:
        raise ValidationError(f"'{name}' cannot be empty", details={"field": name})
    if len(value) > max_len:
        raise ValidationError(f"'{name}' is longer than {max_len} characters",
                              details={"field": name})
    return value


def get_int(
    payload: dict, name: str, *, required: bool = True,
    minimum: int | None = None, maximum: int | None = None,
) -> int | None:
    """Read an integer field, optionally within a range."""
    value = payload.get(name)
    if value is None:
        if required:
            raise ValidationError(f"'{name}' is required", details={"field": name})
        return None
    # bool is a subclass of int, so True would otherwise pass as 1.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"'{name}' must be an integer", details={"field": name})
    if minimum is not None and value < minimum:
        raise ValidationError(f"'{name}' must be at least {minimum}", details={"field": name})
    if maximum is not None and value > maximum:
        raise ValidationError(f"'{name}' must be at most {maximum}", details={"field": name})
    return value


def get_bool(payload: dict, name: str, *, default: bool) -> bool:
    """Read a true/false field."""
    value = payload.get(name, default)
    if not isinstance(value, bool):
        raise ValidationError(f"'{name}' must be true or false", details={"field": name})
    return value


def parse_positive_int(raw: str, name: str) -> int:
    """Parse a query-string value such as ?page=2."""
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"'{name}' must be a positive integer",
                              details={"field": name}) from None
    if value < 1:
        raise ValidationError(f"'{name}' must be a positive integer", details={"field": name})
    return value
