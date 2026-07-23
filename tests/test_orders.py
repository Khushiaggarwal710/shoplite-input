"""Checkout and order history."""

import pytest


def stock_of(client, admin_headers, sku: str) -> int:
    """Read on-hand stock by adjusting by zero."""
    return client.post(f"/admin/inventory/{sku}", headers=admin_headers,
                       json={"change": 0}).get_json()["on_hand"]


def test_checkout_success(client, customer, product, buy, admin_headers):
    """A paid order empties the cart and takes stock."""
    headers, sku = customer(), product(price="250.00", stock=5)
    response = buy(headers, {sku: 2})
    assert response.status_code == 201
    order = response.get_json()
    assert order["status"] == "paid"
    assert order["total_paise"] == 50000 + 4900  # flat shipping under ₹999
    assert order["number"].startswith("SL-")
    assert client.get("/cart", headers=headers).get_json()["items"] == []
    assert stock_of(client, admin_headers, sku) == 3


def test_checkout_empty_cart_is_422(client, customer):
    """You can't check out an empty cart."""
    response = client.post("/orders", headers=customer(), json={"payment_token": "tok_success"})
    assert response.status_code == 422


def test_checkout_requires_payment_token(client, customer, product):
    """payment_token is required and must be a string."""
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": product(), "quantity": 1})
    assert client.post("/orders", headers=headers, json={}).status_code == 422
    assert client.post("/orders", headers=headers, json={"payment_token": 7}).status_code == 422


@pytest.mark.parametrize("pincode", ["", "56000", "056001", "5600011", 560001])
def test_checkout_rejects_bad_pincode(client, customer, product, pincode):
    """shipping_pincode must be a 6-digit string not starting with 0."""
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": product(), "quantity": 1})
    response = client.post("/orders", headers=headers,
                           json={"payment_token": "tok_success", "shipping_pincode": pincode})
    assert response.status_code == 422


def test_checkout_out_of_stock_is_409(client, customer, product, buy):
    """Asking for more than is in stock fails before charging."""
    response = buy(customer(), {product(stock=1): 2})
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "SL-INV-409"


def test_declined_payment_keeps_cart_and_stock(client, customer, product, buy, admin_headers):
    """A declined card leaves a failed order, the cart and the stock untouched."""
    headers, sku = customer(), product(stock=5)
    response = buy(headers, {sku: 1}, payment_token="tok_declined")
    assert response.status_code == 402
    assert response.get_json()["error"]["code"] == "SL-PAY-402"
    order_id = response.get_json()["error"]["details"]["order_id"]
    order = client.get(f"/orders/{order_id}", headers=headers).get_json()
    assert order["status"] == "payment_failed"
    assert len(client.get("/cart", headers=headers).get_json()["items"]) == 1
    assert stock_of(client, admin_headers, sku) == 5


def test_gateway_down_is_502(client, customer, product, buy):
    """An unreachable gateway is a 502, not a crash."""
    response = buy(customer(), {product(): 1}, payment_token="tok_gateway_down")
    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "SL-PAY-502"


def test_order_history_is_own_orders_only(client, customer, product, buy):
    """GET /orders lists only your own orders."""
    first, second, sku = customer(), customer(), product()
    buy(first, {sku: 1})
    buy(second, {sku: 1})
    assert client.get("/orders", headers=first).get_json()["total"] == 1


def test_other_users_order_is_404(client, customer, product, buy, admin_headers):
    """You can't read someone else's order; admins can."""
    owner, other = customer(), customer()
    order_id = buy(owner, {product(): 1}).get_json()["id"]
    assert client.get(f"/orders/{order_id}", headers=other).status_code == 404
    assert client.get(f"/orders/{order_id}", headers=admin_headers).status_code == 200


def test_unknown_order_is_404(client, customer):
    """A missing order ID is a 404."""
    assert client.get("/orders/999", headers=customer()).status_code == 404


def test_price_change_does_not_touch_old_orders(client, customer, product, buy, admin_headers):
    """Order lines keep the price paid."""
    headers, sku = customer(), product(price="100.00")
    order_id = buy(headers, {sku: 1}).get_json()["id"]
    client.patch(f"/admin/products/{sku}", headers=admin_headers, json={"price": "999.00"})
    item = client.get(f"/orders/{order_id}", headers=headers).get_json()["items"][0]
    assert item["unit_price_paise"] == 10000
