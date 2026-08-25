"""Fault switches for incident drills, set by SHOPLITE_FAULT_* variables. All off by default.

SHOPLITE_FAULT_SLOW_QUERY        "on" (1500 ms) or a delay in ms on catalog and report queries
SHOPLITE_FAULT_GATEWAY_ERRORS    "on" (every charge) or a 0-1 rate of charges that time out
SHOPLITE_FAULT_RESERVATION_LEAK  "on" stops expired stock holds from being released
"""

import random
import time

from flask import current_app

OFF_VALUES = {"", "0", "off", "false", "no"}
ON_VALUES = {"1", "on", "true", "yes"}
DEFAULT_SLOW_QUERY_MS = 1500


def setting(name: str) -> str:
    """Read a fault setting, lower-cased."""
    return str(current_app.config.get(name, "off")).strip().lower()


def slow_query_delay_ms() -> int:
    """Extra delay for slow-query drills, in milliseconds (0 when off)."""
    value = setting("SHOPLITE_FAULT_SLOW_QUERY")
    if value in OFF_VALUES:
        return 0
    if value in ON_VALUES:
        return DEFAULT_SLOW_QUERY_MS
    return max(0, int(value))


def maybe_slow_query() -> None:
    """Sleep if the slow-query fault is on."""
    delay_ms = slow_query_delay_ms()
    if delay_ms:
        time.sleep(delay_ms / 1000)


def gateway_error_rate() -> float:
    """Share of charges that should fail (0.0 when off)."""
    value = setting("SHOPLITE_FAULT_GATEWAY_ERRORS")
    if value in OFF_VALUES:
        return 0.0
    if value in ON_VALUES:
        return 1.0
    return min(1.0, max(0.0, float(value)))


def gateway_should_fail() -> bool:
    """Decide whether this charge fails under the gateway-errors fault."""
    rate = gateway_error_rate()
    return rate > 0 and random.random() < rate


def reservation_leak_enabled() -> bool:
    """True when expired stock holds should NOT be released."""
    return setting("SHOPLITE_FAULT_RESERVATION_LEAK") not in OFF_VALUES
