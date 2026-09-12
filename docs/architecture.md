# Architecture

ShopLite is a Flask app built by `create_app()` in `shoplite/__init__.py`.

```
HTTP request
  → shoplite/api/        blueprints: read the request, check login, call a service
  → shoplite/services/   business rules (checkout, pricing, coupons, stock, refunds)
  → shoplite/models/     SQLAlchemy tables
  → SQLite
```

- **Blueprints never hold business rules.** They validate input with `shoplite/utils/validation.py` and call a service. Blueprints are registered once, from the `BLUEPRINTS` list in `shoplite/api/__init__.py`.
- **Errors** are raised as `ShopLiteError` subclasses (`shoplite/errors.py`) and returned in one JSON shape with a stable code.
- **Login** is a bearer token. `login_required` loads the user into `g.current_user`; the admin and reports blueprints check for admins in `before_request`.

## Checkout

`services/checkout.py`:

1. Validate the pincode, the cart and its coupons.
2. Release expired stock holds, create the order, and **hold** stock in `inv_reservation_ledger`.
3. Charge the fake gateway (`payments/gateway.py`).
4. Paid: commit the holds (stock leaves `on_hand`), log coupon use, clear the cart.
5. Declined or gateway error: the order is `payment_failed`; its hold expires after 15 minutes.

## Other services

- **Warehouse:** `warehouse_client.py` pushes stock changes to the `shoplite-warehouse` service. `SHOPLITE_WAREHOUSE_URL=fake` (the default) keeps them in memory. A failed push is logged and counted, and never fails the request.
- **Email:** `notifications/email.py` logs messages instead of sending them.

## Operations

- **Logs:** one JSON line per event on stdout, each with the `request_id` (from `X-Request-ID`, or generated). See `observability.py`.
- **Health:** `GET /healthz` checks the database.
- **Metrics:** `GET /metrics` in Prometheus format: requests, latency, 5xx, checkouts, payments, warehouse failures and held stock.
- **Fault switches** (`faults.py`): `SHOPLITE_FAULT_SLOW_QUERY`, `SHOPLITE_FAULT_GATEWAY_ERRORS`, `SHOPLITE_FAULT_RESERVATION_LEAK`. All are off by default.
- **Docker:** `Dockerfile` runs `flask db upgrade`, then gunicorn with one worker (metrics live in the process).

## Tests

Every test goes through the HTTP client from `tests/conftest.py`. That file is the only test file that imports Flask, so a move to another framework changes the fixtures, not the tests.
