"""Stock holds (reservations) during checkout."""

from datetime import timedelta


def stock_status(client, admin_headers, sku):
    """Read on_hand, reserved and sellable for a SKU."""
    return client.get(f"/admin/inventory/{sku}", headers=admin_headers).get_json()


def test_paid_order_commits_hold(client, admin_headers, customer, product, buy):
    """A paid order leaves stock with nothing held."""
    sku = product(stock=5)
    buy(customer(), {sku: 2})
    assert stock_status(client, admin_headers, sku) | {"warehouse_on_hand": None} == {
        "sku": sku, "on_hand": 3, "reserved": 0, "sellable": 3, "warehouse_on_hand": None}


def test_failed_payment_holds_stock_until_expiry(client, admin_headers, customer, product, buy,
                                                 move_clock):
    """A declined payment keeps its hold for 15 minutes, then it is released."""
    sku = product(stock=2)
    buy(customer(), {sku: 2}, payment_token="tok_declined")
    assert stock_status(client, admin_headers, sku)["sellable"] == 0
    assert buy(customer(), {sku: 1}).status_code == 409
    move_clock(timedelta(minutes=16))
    released = client.post("/admin/stock/release-expired", headers=admin_headers).get_json()
    assert released == {"released": 1}
    assert stock_status(client, admin_headers, sku)["sellable"] == 2


def test_checkout_releases_expired_holds_first(client, customer, product, buy, move_clock):
    """Checkout sweeps expired holds before checking stock."""
    sku = product(stock=1)
    buy(customer(), {sku: 1}, payment_token="tok_declined")
    move_clock(timedelta(minutes=16))
    assert buy(customer(), {sku: 1}).status_code == 201


def test_out_of_stock_leaves_no_hold(client, admin_headers, customer, product, buy):
    """When one line is short, nothing is held for the other lines."""
    plenty, scarce = product(stock=10), product(stock=1)
    assert buy(customer(), {plenty: 2, scarce: 2}).status_code == 409
    assert stock_status(client, admin_headers, plenty)["reserved"] == 0


def test_cannot_write_off_held_stock(client, admin_headers, customer, product, buy):
    """Admins can't reduce stock below the units held for orders."""
    sku = product(stock=3)
    buy(customer(), {sku: 2}, payment_token="tok_declined")
    response = client.post(f"/admin/inventory/{sku}", headers=admin_headers, json={"change": -2})
    assert response.status_code == 422


def test_stock_changes_reach_warehouse(client, admin_headers, customer, product, buy):
    """Restocks and sales are pushed to the (fake) warehouse."""
    sku = product(stock=4)
    client.post(f"/admin/inventory/{sku}", headers=admin_headers, json={"change": 1})
    buy(customer(), {sku: 2})
    assert stock_status(client, admin_headers, sku)["warehouse_on_hand"] == 3
