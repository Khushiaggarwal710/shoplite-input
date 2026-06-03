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
        "SHOPLITE_PORT": env_int("SHOPLITE_PORT", 5000),
        "SHOPLITE_LOG_LEVEL": os.environ.get("SHOPLITE_LOG_LEVEL", "INFO").upper(),
        "SHOPLITE_TOKEN_TTL_HOURS": env_int("SHOPLITE_TOKEN_TTL_HOURS", 24),
        # OWASP's 2023 figure for PBKDF2-SHA256; tests lower it to stay fast.
        "SHOPLITE_PASSWORD_ITERATIONS": env_int("SHOPLITE_PASSWORD_ITERATIONS", 600_000),
    }
    if overrides:
        config.update(overrides)
    return config
