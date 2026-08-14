"""Client for the shoplite-warehouse stock-sync service.

With SHOPLITE_WAREHOUSE_URL=fake (the default) levels are kept in memory, so
ShopLite and its tests never need the warehouse running.
"""

import json
import logging
import urllib.error
import urllib.request

from flask import current_app, g, has_request_context

from shoplite import observability

logger = logging.getLogger("shoplite.warehouse")
TIMEOUT_SECONDS = 2

# Stock levels "sent" in fake mode, keyed by SKU.
fake_levels: dict[str, int] = {}


class WarehouseUnavailable(Exception):
    """The warehouse service could not be reached or returned an error."""


def base_url() -> str:
    """The configured warehouse URL, or 'fake'."""
    return current_app.config["SHOPLITE_WAREHOUSE_URL"].rstrip("/")


def call(method: str, path: str, payload: dict | None = None) -> dict:
    """Send one JSON request to the warehouse service."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if has_request_context() and g.get("request_id"):
        headers[observability.REQUEST_ID_HEADER] = g.request_id  # one ID across both services
    request = urllib.request.Request(f"{base_url()}{path}", data=data, method=method,
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read() or b"{}")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise WarehouseUnavailable(f"{method} {path} failed: {exc}") from exc


def push_stock_level(sku: str, on_hand: int) -> bool:
    """Send a new on-hand count; failures are logged and counted, never raised."""
    if base_url() == "fake":
        fake_levels[sku] = on_hand
        return True
    try:
        call("PUT", f"/stock/{sku}", {"on_hand": on_hand})
        return True
    except WarehouseUnavailable as exc:
        logger.warning("warehouse sync failed for %s: %s", sku, exc)
        observability.count("shoplite_warehouse_sync_failures_total")
        return False


def fetch_stock_level(sku: str) -> int | None:
    """Ask the warehouse for its count of a SKU (None if it has none)."""
    if base_url() == "fake":
        return fake_levels.get(sku)
    return call("GET", f"/stock/{sku}").get("on_hand")
