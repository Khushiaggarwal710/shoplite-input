"""Admin reports."""


def test_sales_summary_counts_paid_orders_only(client, admin_headers, customer, product, buy):
    """Failed payments are not revenue."""
    headers, sku = customer(), product(price="1000.00")
    buy(headers, {sku: 1})
    buy(headers, {sku: 1}, payment_token="tok_declined")
    body = client.get("/reports/sales-summary", headers=admin_headers).get_json()
    assert body["orders"] == 1
    assert body["revenue_paise"] == 100000


def test_top_products_orders_by_units(client, admin_headers, customer, product, buy):
    """Best sellers come first."""
    headers, first, second = customer(), product(sku="AAA-1"), product(sku="BBB-1")
    buy(headers, {first: 1, second: 3})
    items = client.get("/reports/top-products?limit=1", headers=admin_headers).get_json()["items"]
    assert [(i["sku"], i["units_sold"]) for i in items] == [("BBB-1", 3)]


def test_low_stock_uses_sellable_units(client, admin_headers, product):
    """Only products at or below the threshold are listed."""
    product(sku="LOW-1", stock=2)
    product(sku="HIGH-1", stock=50)
    items = client.get("/reports/low-stock?threshold=5", headers=admin_headers).get_json()["items"]
    assert [i["sku"] for i in items] == ["LOW-1"]


def test_report_inputs_are_validated(client, admin_headers):
    """Bad dates and reversed ranges are 422s."""
    url = "/reports/sales-summary"
    assert client.get(f"{url}?start=yesterday", headers=admin_headers).status_code == 422
    reversed_range = f"{url}?start=2026-10-02&end=2026-10-01"
    assert client.get(reversed_range, headers=admin_headers).status_code == 422


def test_report_params_cannot_inject_sql(client, admin_headers, customer, product, buy):
    """A quote in a parameter is treated as data, not SQL."""
    buy(customer(), {product(): 1})
    response = client.get("/reports/sales-summary?start=2026-01-01' OR '1'='1",
                          headers=admin_headers)
    assert response.status_code == 422


def test_reports_are_admin_only(client, customer):
    """Customers get 403."""
    assert client.get("/reports/low-stock", headers=customer()).status_code == 403
