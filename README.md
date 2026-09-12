# ShopLite

A small online-shop backend: a JSON API for a fictional store, written in Flask.

All data is synthetic. Any similarity to real companies or people is coincidental.

## Quick start

```bash
uv sync                                   # create .venv from uv.lock
uv run python scripts/seed.py             # build instance/shoplite.db with demo data
uv run flask --app shoplite run --port 5000
uv run pytest                             # run the tests
uv run ruff check .                       # lint
```

Demo logins (password `shoplite-demo-1`): `admin@shoplite.example`, or any customer such as `aarav.sharma@example.com`.

With Docker:

```bash
docker build -t shoplite .
docker run -p 5000:5000 shoplite         # then: curl localhost:5000/healthz
```

## Layout

| Path | What it holds |
|---|---|
| `shoplite/api/` | HTTP endpoints (Flask blueprints) |
| `shoplite/services/` | Business rules: checkout, pricing, coupons, stock, shipping, refunds, reports |
| `shoplite/models/` | Database tables (SQLAlchemy) |
| `shoplite/payments/` | A fake payment gateway (no network) |
| `shoplite/notifications/` | Email stub (logs instead of sending) |
| `shoplite/utils/` | Money, validation, pagination, IDs, clock |
| `shoplite/observability.py` | JSON logs, request IDs and metrics |
| `shoplite/faults.py` | Fault switches for incident drills |
| `shoplite/warehouse_client.py` | Calls to the shoplite-warehouse service |
| `migrations/` | Alembic schema migrations |
| `scripts/seed.py`, `fixtures/` | Deterministic demo data |
| `sql/` | Reporting views |
| `docs/` | API, data model and architecture |
| `tests/` | pytest suite; every test goes through the HTTP client |

## Configuration

All settings are environment variables; see `.env.example`.
