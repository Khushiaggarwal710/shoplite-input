# ShopLite

A small online-shop backend: a JSON API for a fictional store, written in Flask.

All data is synthetic. Any similarity to real companies or people is coincidental.

## Quick start

```bash
uv sync                      # create .venv from uv.lock
uv run flask --app shoplite db upgrade
uv run flask --app shoplite run --port 5000
uv run pytest                # run the tests
```

## Layout

| Folder | What it holds |
|---|---|
| `shoplite/models/` | Database tables (SQLAlchemy) |
| `shoplite/services/` | Business rules: checkout, pricing, coupons, stock, shipping, refunds |
| `shoplite/api/` | HTTP endpoints (Flask blueprints) |
| `shoplite/payments/` | A fake payment gateway (no network) |
| `shoplite/notifications/` | Email stub (logs instead of sending) |
| `shoplite/utils/` | Money, validation, pagination, IDs |
| `migrations/` | Alembic schema migrations |
| `tests/` | pytest suite; every test goes through the HTTP client |
