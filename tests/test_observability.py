"""Logs, request IDs, health check and metrics."""

import json


def test_request_id_is_generated_or_echoed(client):
    """Responses carry X-Request-ID; a safe incoming ID is reused."""
    assert len(client.get("/healthz").headers["X-Request-ID"]) == 32
    echoed = client.get("/healthz", headers={"X-Request-ID": "abc-123"})
    assert echoed.headers["X-Request-ID"] == "abc-123"


def test_unsafe_request_id_is_replaced(client):
    """IDs with spaces or odd characters are not trusted."""
    response = client.get("/healthz", headers={"X-Request-ID": "bad id <script>"})
    assert response.headers["X-Request-ID"] != "bad id <script>"
    assert len(response.headers["X-Request-ID"]) == 32


def test_access_log_is_json_with_request_id(app_factory, capsys):
    """Each request writes one JSON access line with its request ID."""
    client = app_factory()  # built here so its log handler writes to the captured stdout
    client.get("/products", headers={"X-Request-ID": "log-test-1"})
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line]
    access = [line for line in lines if line["logger"] == "shoplite.access"][-1]
    assert access["request_id"] == "log-test-1"
    assert access["route"] == "/products"
    assert access["status"] == 200


def test_healthz(client):
    """The health check reports the database and version."""
    body = client.get("/healthz").get_json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_metrics_count_requests_and_checkouts(client, customer, product, buy):
    """/metrics exposes request, checkout and payment counters."""
    buy(customer(), {product(): 1})
    buy(customer(), {product(): 1}, payment_token="tok_declined")
    text = client.get("/metrics").get_data(as_text=True)
    assert 'shoplite_checkouts_total{outcome="paid"} 1' in text
    assert 'shoplite_checkouts_total{outcome="declined"} 1' in text
    assert 'shoplite_payments_total{status="declined"} 1' in text
    assert 'route="/orders"' in text
    assert "shoplite_http_request_duration_seconds_bucket" in text


def test_metrics_reserved_units_gauge(client, customer, product, buy):
    """Declined orders hold nothing, so the gauge stays at zero."""
    buy(customer(), {product(stock=5): 3}, payment_token="tok_declined")
    assert "shoplite_stock_reserved_units 0" in client.get("/metrics").get_data(as_text=True)
