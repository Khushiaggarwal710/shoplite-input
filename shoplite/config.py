"""App settings, read from SHOPLITE_* environment variables."""

import os

# Relative SQLite paths resolve inside the Flask instance folder (instance/).
DEFAULT_DB_URL = "sqlite:///shoplite.db"


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable, or return the default."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def load_config(overrides: dict | None = None) -> dict:
    """Build the settings for one app: environment first, then overrides."""
    config = {
        "SQLALCHEMY_DATABASE_URI": os.environ.get("SHOPLITE_DB_URL", DEFAULT_DB_URL),
        "SHOPLITE_LOG_LEVEL": os.environ.get("SHOPLITE_LOG_LEVEL", "INFO").upper(),
        "SHOPLITE_TOKEN_TTL_HOURS": env_int("SHOPLITE_TOKEN_TTL_HOURS", 24),
        # OWASP's 2023 figure for PBKDF2-SHA256; tests lower it to stay fast.
        "SHOPLITE_PASSWORD_ITERATIONS": env_int("SHOPLITE_PASSWORD_ITERATIONS", 600_000),
        # "fake" keeps everything in-process; otherwise the warehouse service's base URL.
        "SHOPLITE_WAREHOUSE_URL": os.environ.get("SHOPLITE_WAREHOUSE_URL", "fake"),
        # Fault switches for incident drills. All off by default.
        "SHOPLITE_FAULT_SLOW_QUERY": os.environ.get("SHOPLITE_FAULT_SLOW_QUERY", "off"),
        "SHOPLITE_FAULT_GATEWAY_ERRORS": os.environ.get("SHOPLITE_FAULT_GATEWAY_ERRORS", "off"),
        "SHOPLITE_FAULT_RESERVATION_LEAK": os.environ.get("SHOPLITE_FAULT_RESERVATION_LEAK", "off"),
    }
    if overrides:
        config.update(overrides)
    return config
