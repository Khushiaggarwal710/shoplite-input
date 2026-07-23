"""Refunds."""

from shoplite.notifications.email import outbox


def test_refund_restocks_and_marks_payment(client, admin_headers, customer, product, buy):
    """A refund sets the order to refunded and returns the stock."""
    headers, sku = customer("refund@shoplite.test"), product(stock=3)
    order_id = buy(headers, {sku: 2}).get_json()["id"]
    response = client.post(f"/orders/{order_id}/refund", headers=admin_headers)
    assert response.get_json()["status"] == "refunded"
    stock = client.post(f"/admin/inventory/{sku}", headers=admin_headers, json={"change": 0})
    assert stock.get_json()["on_hand"] == 3
    payments = client.get(f"/orders/{order_id}/payments", headers=headers).get_json()["items"]
    assert payments[-1]["status"] == "refunded"
    assert outbox[-1]["to"] == "refund@shoplite.test"


def test_refund_twice_is_409(client, admin_headers, customer, product, buy):
    """An order can only be refunded once."""
    order_id = buy(customer(), {product(): 1}).get_json()["id"]
    client.post(f"/orders/{order_id}/refund", headers=admin_headers)
    again = client.post(f"/orders/{order_id}/refund", headers=admin_headers)
    assert again.status_code == 409


def test_customers_cannot_refund(client, customer, product, buy):
    """Refunds are admin-only, even for your own order."""
    headers = customer()
    order_id = buy(headers, {product(): 1}).get_json()["id"]
    assert client.post(f"/orders/{order_id}/refund", headers=headers).status_code == 403
