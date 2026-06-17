"""The shopping cart."""


def test_cart_needs_login(client):
    """Anonymous users have no cart."""
    assert client.get("/cart").status_code == 401


def test_add_items_merges_lines(client, customer, product):
    """Adding the same SKU twice merges into one line."""
    headers, sku = customer(), product(price="100.00")
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    body = client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 2}).get_json()
    assert body["items"][0]["quantity"] == 3
    assert body["subtotal_paise"] == 30000


def test_quantity_must_be_positive_integer(client, customer, product):
    """Zero, negatives, strings and booleans are rejected."""
    headers, sku = customer(), product()
    for bad in (0, -1, "2", True, 1.5):
        response = client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": bad})
        assert response.status_code == 422, bad


def test_line_quantity_is_capped(client, customer, product):
    """At most 20 units of one product."""
    headers, sku = customer(), product()
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 15})
    response = client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 6})
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "SL-CART-422"


def test_unknown_sku_is_404(client, customer):
    """You can't add a product that doesn't exist."""
    response = client.post("/cart/items", headers=customer(), json={"sku": "NOPE", "quantity": 1})
    assert response.status_code == 404


def test_set_quantity_and_remove(client, customer, product):
    """PUT changes quantity; DELETE removes the line."""
    headers, sku = customer(), product()
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    assert client.put(f"/cart/items/{sku}", headers=headers,
                      json={"quantity": 4}).get_json()["items"][0]["quantity"] == 4
    assert client.delete(f"/cart/items/{sku}", headers=headers).get_json()["items"] == []


def test_change_missing_line_is_404(client, customer, product):
    """Changing a SKU that isn't in the cart is a 404."""
    response = client.put(f"/cart/items/{product()}", headers=customer(), json={"quantity": 1})
    assert response.get_json()["error"]["code"] == "SL-CART-404"


def test_carts_are_per_user(client, customer, product):
    """One user's cart is not visible to another."""
    first, second, sku = customer(), customer(), product()
    client.post("/cart/items", headers=first, json={"sku": sku, "quantity": 1})
    assert client.get("/cart", headers=second).get_json()["items"] == []
