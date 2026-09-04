"""Calls to the shoplite-warehouse service."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


class FakeWarehouse(BaseHTTPRequestHandler):
    """A tiny stand-in for the warehouse HTTP API."""

    levels: dict = {}
    request_ids: list = []

    def do_PUT(self):
        """Store a stock level."""
        self.request_ids.append(self.headers.get("X-Request-ID"))
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.levels[self.path.rsplit("/", 1)[-1]] = body["on_hand"]
        self.send_json({"ok": True})

    def do_GET(self):
        """Return a stock level."""
        self.send_json({"on_hand": self.levels.get(self.path.rsplit("/", 1)[-1])})

    def send_json(self, payload: dict) -> None:
        """Write a 200 JSON response."""
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        """Keep test output quiet."""


@pytest.fixture
def warehouse_url():
    """Run the fake warehouse on a free local port."""
    server = HTTPServer(("127.0.0.1", 0), FakeWarehouse)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_http_mode_pushes_and_reads_levels(shop_with, warehouse_url):
    """Restocks are sent to the warehouse and read back."""
    shop = shop_with(SHOPLITE_WAREHOUSE_URL=warehouse_url)
    shop.client.post(f"/admin/inventory/{shop.sku}",
                     headers={**shop.admin_headers, "X-Request-ID": "trace-42"},
                     json={"change": 2})
    assert FakeWarehouse.request_ids[-1] == "trace-42"
    status = shop.client.get(f"/admin/inventory/{shop.sku}", headers=shop.admin_headers)
    assert status.get_json()["warehouse_on_hand"] == 7


def test_unreachable_warehouse_does_not_break_restock(shop_with):
    """If the warehouse is down, the restock still succeeds and the failure is counted."""
    shop = shop_with(SHOPLITE_WAREHOUSE_URL="http://127.0.0.1:9")  # nothing listens on port 9
    response = shop.client.post(f"/admin/inventory/{shop.sku}", headers=shop.admin_headers,
                                json={"change": 1})
    assert response.status_code == 200
    status = shop.client.get(f"/admin/inventory/{shop.sku}", headers=shop.admin_headers)
    assert status.get_json()["warehouse_on_hand"] is None
    metrics = shop.client.get("/metrics").get_data(as_text=True)
    assert "shoplite_warehouse_sync_failures_total 1" in metrics
