"""Shipping orders."""

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
