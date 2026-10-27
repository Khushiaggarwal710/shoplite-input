"""Shipping charges and shipping orders."""

import pytest

from shoplite.notifications.email import outbox


def test_ship_paid_order(client, admin_headers, customer, product, buy):
    """Shipping a paid order creates a tracking code and emails the customer."""
    order_id = buy(customer("ship@shoplite.test"), {product(): 1}).get_json()["id"]
    response = client.post(f"/admin/orders/{order_id}/ship", headers=admin_headers,
                           json={"carrier": "BlueDart"})
    assert response.status_code == 201
    assert response.get_json()["tracking_code"] == f"SLX{order_id:08d}"
    assert outbox[-1]["to"] == "ship@shoplite.test"


def test_cannot_ship_unpaid_or_twice(client, admin_headers, customer, product, buy):
    """Failed or already-shipped orders can't be shipped."""
    headers, sku = customer(), product()
    failed = buy(headers, {sku: 1}, payment_token="tok_declined").get_json()["error"]["details"]
    url = f"/admin/orders/{failed['order_id']}/ship"
    assert client.post(url, headers=admin_headers, json={"carrier": "DTDC"}).status_code == 409
    paid = buy(headers, {sku: 1}).get_json()["id"]
    client.post(f"/admin/orders/{paid}/ship", headers=admin_headers, json={"carrier": "DTDC"})
    url = f"/admin/orders/{paid}/ship"
    again = client.post(url, headers=admin_headers, json={"carrier": "DTDC"})
    assert again.get_json()["error"]["code"] == "SL-ORD-409"


def test_ship_unknown_order_is_404(client, admin_headers):
    """Unknown order IDs are 404."""
    response = client.post("/admin/orders/999/ship", headers=admin_headers, json={"carrier": "X"})
    assert response.status_code == 404


@pytest.mark.parametrize("pincode, rate", [
    ("560001", 3900),  # Bengaluru, south
    ("110001", 5900),  # Delhi, north
    ("400001", 5900),  # Mumbai, west
    ("700001", 6900),  # Kolkata, east
    ("781001", 9900),  # Guwahati, northeast
    ("795001", 9900),  # Imphal, northeast
    ("900001", 9900),  # Army Postal Service
])
def test_rate_depends_on_zone(client, customer, product, pincode, rate):
    """Orders under ₹999 pay the zone rate for their PIN code."""
    headers, sku = customer(), product(price="100.00")
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    order = client.post("/orders", headers=headers,
                        json={"payment_token": "tok_success", "shipping_pincode": pincode})
    assert order.get_json()["shipping_paise"] == rate


def test_free_shipping_applies_in_every_zone(client, customer, product):
    """₹999 and above ships free, even to the northeast."""
    headers, sku = customer(), product(price="999.00")
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    order = client.post("/orders", headers=headers,
                        json={"payment_token": "tok_success", "shipping_pincode": "795001"})
    assert order.get_json()["shipping_paise"] == 0


def test_cart_quotes_standard_rate_before_pincode(client, customer, product):
    """The cart has no address yet, so it shows the ₹49 standard rate."""
    headers = customer()
    cart = client.post("/cart/items", headers=headers,
                       json={"sku": product(price="100.00"), "quantity": 1}).get_json()
    assert cart["shipping_paise"] == 4900
