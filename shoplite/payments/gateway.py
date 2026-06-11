"""A fake payment gateway. It never calls the network.

Test card tokens: tok_success (charged), tok_declined (declined),
tok_gateway_down (gateway unreachable). Any other token is declined.
"""

import hashlib
from dataclasses import dataclass


class GatewayUnavailable(Exception):
    """The gateway could not be reached."""


@dataclass
class ChargeResult:
    """Outcome of one charge."""

    succeeded: bool
    gateway_ref: str | None = None
    error_code: str | None = None


def make_ref(prefix: str, key: str) -> str:
    """Build a stable gateway reference from an idempotency key."""
    return f"{prefix}_{hashlib.sha256(key.encode()).hexdigest()[:16]}"


def charge(amount_paise: int, payment_token: str, idempotency_key: str) -> ChargeResult:
    """Charge a card token; the same idempotency key always gives the same reference."""
    if amount_paise <= 0:
        raise ValueError("charge amount must be positive")
    if payment_token == "tok_gateway_down":
        raise GatewayUnavailable("payment gateway timed out")
    if payment_token == "tok_success":
        return ChargeResult(succeeded=True, gateway_ref=make_ref("ch", idempotency_key))
    return ChargeResult(succeeded=False, error_code="SL-PAY-402")


def refund(gateway_ref: str, amount_paise: int) -> str:
    """Refund a charge and return the refund reference."""
    if amount_paise <= 0:
        raise ValueError("refund amount must be positive")
    return make_ref("re", gateway_ref)
