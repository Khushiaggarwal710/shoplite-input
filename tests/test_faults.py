"""Fault switches for incident drills."""

import time
from datetime import timedelta

import pytest

CHECKOUT = {"payment_token": "tok_success", "shipping_pincode": "560001"}


def test_faults_are_off_by_default(client, customer, product, buy):
    """With no switches set, checkout works normally."""
    assert buy(customer(), {product(): 1}).status_code == 201


def test_gateway_errors_fault(shop_with):
    """SHOPLITE_FAULT_GATEWAY_ERRORS=on makes every charge time out."""
    shop = shop_with(SHOPLITE_FAULT_GATEWAY_ERRORS="on")
    shop.client.post("/cart/items", headers=shop.customer_headers,
                     json={"sku": shop.sku, "quantity": 1})
    response = shop.client.post("/orders", headers=shop.customer_headers, json=CHECKOUT)
    assert response.status_code == 502
    metrics = shop.client.get("/metrics").get_data(as_text=True)
    assert 'shoplite_checkouts_total{outcome="gateway_error"} 1' in metrics


def test_gateway_errors_rate_zero_is_off(shop_with):
    """A rate of 0 lets every charge through."""
    shop = shop_with(SHOPLITE_FAULT_GATEWAY_ERRORS="0")
    shop.client.post("/cart/items", headers=shop.customer_headers,
                     json={"sku": shop.sku, "quantity": 1})
    assert shop.client.post("/orders", headers=shop.customer_headers,
                            json=CHECKOUT).status_code == 201


def test_slow_query_fault(app_factory, monkeypatch):
    """SHOPLITE_FAULT_SLOW_QUERY=<ms> delays catalog queries."""
    delays = []
    monkeypatch.setattr(time, "sleep", delays.append)
    app_factory(SHOPLITE_FAULT_SLOW_QUERY="250").get("/products")
    assert delays == [0.25]


def test_reservation_leak_fault(shop_with, move_clock):
    """SHOPLITE_FAULT_RESERVATION_LEAK=on stops expired holds from being released."""
    shop = shop_with(SHOPLITE_FAULT_RESERVATION_LEAK="on")
    shop.client.post("/cart/items", headers=shop.customer_headers,
                     json={"sku": shop.sku, "quantity": 1})
    shop.client.post("/orders", headers=shop.customer_headers,
                     json={**CHECKOUT, "payment_token": "tok_declined"})
    move_clock(timedelta(hours=1))
    released = shop.client.post("/admin/stock/release-expired", headers=shop.admin_headers)
    assert released.get_json()["released"] == 0
    assert "shoplite_stock_reserved_units 1" in shop.client.get("/metrics").get_data(as_text=True)


@pytest.mark.parametrize("value", ["maybe", "-3x"])
def test_bad_fault_value_is_an_error(app_factory, value):
    """A malformed switch value fails loudly instead of being ignored."""
    assert app_factory(SHOPLITE_FAULT_SLOW_QUERY=value).get("/products").status_code == 500
