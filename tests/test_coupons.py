"""Coupons."""

from datetime import UTC, datetime, timedelta


def test_percent_coupon_discounts_order(client, customer, product, coupon, buy):
    """A 10% coupon takes 10% off the subtotal."""
    code = coupon("TENOFF", value=10)
    order = buy(customer(), {product(price="500.00"): 2}, coupon=code).get_json()
    assert order["discount_paise"] == 10000
    assert order["total_paise"] == 100000 - 10000 + 3900


def test_flat_coupon_never_exceeds_subtotal(client, customer, product, coupon):
    """A flat coupon bigger than the cart only takes the cart's value."""
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": product(price="20.00"), "quantity": 1})
    code = coupon("BIGFLAT", kind="flat", value=500000)
    cart = client.post("/cart/coupons", headers=headers, json={"code": code}).get_json()
    assert cart["discount_paise"] == 2000
    assert cart["total_paise"] == 4900  # shipping only


def test_only_one_coupon_per_order(client, customer, product, coupon):
    """A second coupon is rejected with SL-CPN-409."""
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": product(), "quantity": 1})
    client.post("/cart/coupons", headers=headers, json={"code": coupon("FIRST")})
    response = client.post("/cart/coupons", headers=headers, json={"code": coupon("SECOND")})
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "SL-CPN-409"


def test_minimum_subtotal(client, customer, product, coupon):
    """A coupon with a minimum subtotal is refused on a smaller cart."""
    headers = customer()
    sku = product(price="100.00")
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    code = coupon("MIN1000", min_subtotal_paise=100000)
    response = client.post("/cart/coupons", headers=headers, json={"code": code})
    assert response.get_json()["error"]["code"] == "SL-CPN-422"


def test_expired_coupon_rejected_at_checkout(client, customer, product, coupon, move_clock):
    """A coupon that expires between applying and paying fails checkout."""
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": product(), "quantity": 1})
    expiry = (datetime.now(UTC) + timedelta(hours=1)).replace(tzinfo=None).isoformat()
    client.post("/cart/coupons", headers=headers, json={"code": coupon("SOON", expires_at=expiry)})
    move_clock(timedelta(hours=2))
    response = client.post("/orders", headers=headers,
                           json={"payment_token": "tok_success", "shipping_pincode": "560001"})
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "SL-CPN-422"


def test_max_redemptions(client, customer, product, coupon, buy):
    """A coupon limited to one use can't be applied after it's used."""
    code, sku = coupon("ONCE", max_redemptions=1), product()
    assert buy(customer(), {sku: 1}, coupon=code).status_code == 201
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    response = client.post("/cart/coupons", headers=headers, json={"code": code})
    assert response.get_json()["error"]["code"] == "SL-CPN-422"


def test_declined_payment_does_not_use_coupon(client, customer, product, coupon, buy):
    """Only paid orders count as redemptions."""
    code, sku = coupon("RETRY", max_redemptions=1), product()
    assert buy(customer(), {sku: 1}, payment_token="tok_declined", coupon=code).status_code == 402
    assert buy(customer(), {sku: 1}, coupon=code).status_code == 201


def test_unknown_and_removed_coupons(client, customer, product, coupon):
    """Unknown codes are 404; codes are case-insensitive; removal works."""
    headers = customer()
    client.post("/cart/items", headers=headers, json={"sku": product(), "quantity": 1})
    unknown = client.post("/cart/coupons", headers=headers, json={"code": "NOPE"})
    assert unknown.status_code == 404
    client.post("/cart/coupons", headers=headers, json={"code": coupon("CASE").lower()})
    assert client.delete("/cart/coupons/case", headers=headers).get_json()["coupons"] == []


def test_create_coupon_validation(client, admin_headers, customer):
    """Bad kinds and percent values are rejected; customers can't create coupons."""
    bad_kind = client.post("/coupons", headers=admin_headers,
                           json={"code": "X1", "kind": "bogo", "value": 1})
    assert bad_kind.status_code == 422
    too_much = client.post("/coupons", headers=admin_headers,
                           json={"code": "X2", "kind": "percent", "value": 150})
    assert too_much.status_code == 422
    forbidden = client.post("/coupons", headers=customer(),
                            json={"code": "X3", "kind": "flat", "value": 100})
    assert forbidden.status_code == 403
