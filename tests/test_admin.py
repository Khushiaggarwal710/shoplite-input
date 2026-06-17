"""Admin endpoints."""


def test_admin_routes_reject_customers(client, customer):
    """Customers get 403; anonymous users get 401."""
    assert client.get("/admin/orders", headers=customer()).status_code == 403
    assert client.get("/admin/orders").status_code == 401


def test_create_product_validates_price(client, admin_headers):
    """Prices are rupee strings with at most two decimals."""
    base = {"sku": "BAD-1", "name": "Bad", "category": "Misc"}
    for bad in ("12.345", "-1", "abc", 499):
        body = {**base, "price": bad}
        response = client.post("/admin/products", headers=admin_headers, json=body)
        assert response.status_code == 422, bad


def test_duplicate_sku_is_409(client, admin_headers, product):
    """SKUs are unique."""
    sku = product()
    response = client.post("/admin/products", headers=admin_headers, json={
        "sku": sku, "name": "Again", "price": "1.00", "category": "Misc"})
    assert response.get_json()["error"]["code"] == "SL-CAT-409"


def test_update_product_price(client, admin_headers, product):
    """PATCH changes the price."""
    sku = product()
    url = f"/admin/products/{sku}"
    response = client.patch(url, headers=admin_headers, json={"price": "75.25"})
    assert response.get_json()["price_paise"] == 7525


def test_adjust_inventory(client, admin_headers, product):
    """Stock can be added and removed but not go negative."""
    sku = product(stock=2)
    url = f"/admin/inventory/{sku}"
    assert client.post(url, headers=admin_headers, json={"change": 3}).get_json()["on_hand"] == 5
    response = client.post(url, headers=admin_headers, json={"change": -6})
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "SL-INV-422"


def test_admin_order_list_filters_by_status(client, admin_headers, customer, product, buy):
    """?status= filters the admin order list."""
    headers, sku = customer(), product()
    buy(headers, {sku: 1})
    buy(headers, {sku: 1}, payment_token="tok_declined")
    body = client.get("/admin/orders?status=payment_failed", headers=admin_headers).get_json()
    assert body["total"] == 1


def test_unknown_route_is_json_404(client):
    """Flask's own 404 comes back in the JSON error shape."""
    response = client.get("/no-such-route")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "SL-HTTP-404"
