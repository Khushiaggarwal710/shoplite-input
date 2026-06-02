"""Bearer tokens and order numbers."""

import hashlib
import secrets
from datetime import datetime


def new_token() -> str:
    """Return a new random bearer token."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a token (only the digest is stored)."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def order_number(order_id: int, created_at: datetime) -> str:
    """Return the customer-facing order number, e.g. SL-20260613-000042."""
    return f"SL-{created_at:%Y%m%d}-{order_id:06d}"
