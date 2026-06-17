"""Public product catalog."""


def test_list_products_is_paginated(client, product):
    """Lists report page, per_page and total."""
    for _ in range(3):
        product()
    body = client.get("/products?per_page=2").get_json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["per_page"] == 2


def test_per_page_is_capped(client, product):
    """per_page can't exceed 100."""
    product()
    assert client.get("/products?per_page=5000").get_json()["per_page"] == 100


def test_bad_page_number_is_422(client):
    """page must be a positive integer."""
    assert client.get("/products?page=zero").status_code == 422
    assert client.get("/products?page=0").status_code == 422


def test_filter_by_category_and_search(client, product):
    """?category= and ?q= narrow the list."""
    product(sku="KIT-1", category="Kitchen")
    product(sku="TOY-1", category="Toys")
    kitchen = client.get("/products?category=kitchen").get_json()["items"]
    assert [p["sku"] for p in kitchen] == ["KIT-1"]
    found = client.get("/products?q=TOY-1").get_json()["items"]
    assert [p["sku"] for p in found] == ["TOY-1"]


def test_get_product_and_unknown_sku(client, product):
    """A known SKU returns the product; an unknown one is a 404."""
    sku = product(price="249.50")
    assert client.get(f"/products/{sku}").get_json()["price_paise"] == 24950
    missing = client.get("/products/NOPE-1")
    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "SL-CAT-404"


def test_inactive_products_are_hidden(client, product, admin_headers):
    """Deactivated products disappear from the public catalog."""
    sku = product()
    client.patch(f"/admin/products/{sku}", headers=admin_headers, json={"is_active": False})
    assert client.get(f"/products/{sku}").status_code == 404
    assert client.get("/products").get_json()["total"] == 0


def test_categories_are_listed(client, product):
    """Categories created with products are listed with slugs."""
    product(category="Home & Kitchen")
    assert client.get("/categories").get_json()["items"][0]["slug"] == "home-kitchen"
