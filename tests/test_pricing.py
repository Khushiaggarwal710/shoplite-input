"""Cart pricing and shipping charges."""

from shoplite.utils.money import percent_of


def test_free_shipping_from_999(client, customer, product):
    """Orders of ₹999 or more ship free; below that pay ₹49."""
    headers = customer()
    sku = product(price="999.00")
    cart = client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1}).get_json()
    assert cart["shipping_paise"] == 0
    cart = client.put(f"/cart/items/{sku}", headers=headers, json={"quantity": 0}).get_json()
    assert cart["shipping_paise"] == 0  # empty cart pays nothing


def test_discount_can_drop_order_below_free_shipping(client, customer, product, coupon):
    """Free shipping is judged after the discount."""
    headers = customer()
    sku = product(price="1000.00")
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    cart = client.post("/cart/coupons", headers=headers,
                       json={"code": coupon("FIVE", value=5)}).get_json()
    assert cart["discount_paise"] == 5000
    assert cart["shipping_paise"] == 4900


def test_percent_of_rounds_half_up():
    """12.5% of 1 paisa rounds to 0; 50% of 1 paisa rounds to 1."""
    assert percent_of(1, 12) == 0
    assert percent_of(1, 50) == 1
    assert percent_of(99_999, 10) == 10_000
