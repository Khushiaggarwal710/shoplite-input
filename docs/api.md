# ShopLite API

JSON in, JSON out. Amounts are integer **paise** (₹1 = 100 paise). Send the token from `/auth/login` as `Authorization: Bearer <token>`.

## Endpoints

| Method | Path | Who | What it does |
|---|---|---|---|
| POST | `/auth/register` | anyone | Create a customer account: `email`, `name`, `password` (8+ characters) |
| POST | `/auth/login` | anyone | Returns `{"token", "token_type"}`; tokens last 24 hours |
| POST | `/auth/logout` | customer | Revoke the current token |
| GET | `/auth/me` | customer | The logged-in user |
| GET | `/products` | anyone | Active products; `?category=`, `?q=`, `?page=`, `?per_page=` (max 100) |
| GET | `/products/<sku>` | anyone | One product |
| GET | `/categories` | anyone | All categories |
| GET | `/products/<sku>/reviews` | anyone | Reviews plus `rating` (count and average) |
| POST | `/products/<sku>/reviews` | buyer | `rating` (1–5), `title`, optional `body`; one per product |
| GET | `/cart` | customer | Cart with subtotal, discount, shipping and total |
| POST | `/cart/items` | customer | Add `sku`, `quantity` (1–20 per product) |
| PUT | `/cart/items/<sku>` | customer | Set `quantity`; 0 removes the line |
| DELETE | `/cart/items/<sku>` | customer | Remove the line |
| POST | `/cart/coupons` | customer | Apply a coupon `code` (one per order) |
| DELETE | `/cart/coupons/<code>` | customer | Remove a coupon |
| POST | `/orders` | customer | Check out: `payment_token`, `shipping_pincode` |
| GET | `/orders` | customer | Your orders, newest first (paginated) |
| GET | `/orders/<id>` | owner or admin | One order |
| GET | `/orders/<id>/payments` | owner or admin | Charge attempts for the order |
| POST | `/orders/<id>/refund` | admin | Full refund; items go back to stock |
| POST | `/coupons` | admin | Create a coupon: `code`, `kind` (`percent` or `flat`), `value`, optional `min_subtotal_paise`, `max_redemptions`, `expires_at` |
| GET | `/coupons` | admin | All coupons |
| POST | `/admin/products` | admin | Create a product: `sku`, `name`, `price` (rupees as a string, e.g. `"499.00"`), `category`, optional `description`, `stock` |
| PATCH | `/admin/products/<sku>` | admin | Change `name`, `description`, `price` or `is_active` |
| POST | `/admin/inventory/<sku>` | admin | Restock or write off: `{"change": 10}` |
| GET | `/admin/inventory/<sku>` | admin | On hand, held, sellable, and the warehouse's count |
| POST | `/admin/stock/release-expired` | admin | Release stock holds older than 15 minutes |
| GET | `/admin/orders` | admin | All orders; `?status=` |
| POST | `/admin/orders/<id>/ship` | admin | Ship a paid order: `carrier` |
| GET | `/reports/sales-summary` | admin | Orders, revenue, discounts, average order; `?start=`, `?end=` (ISO dates, default last 30 days) |
| GET | `/reports/top-products` | admin | Best sellers by units; `?limit=` (max 50) |
| GET | `/reports/low-stock` | admin | Sellable stock at or below `?threshold=` (default 5) |
| GET | `/healthz` | anyone | `200` when the database answers, `503` otherwise |
| GET | `/metrics` | anyone | Prometheus text format |

Test card tokens for the fake gateway: `tok_success`, `tok_declined`, `tok_gateway_down`.

## Errors

Every error has the same shape:

```json
{"error": {"code": "SL-INV-409", "message": "only 1 left of KIT-0007", "details": {"sku": "KIT-0007"}}}
```

| Code | HTTP | Meaning |
|---|---|---|
| `SL-VAL-422` | 422 | A field is missing, the wrong type or out of range; `details.field` names it |
| `SL-AUTH-401` | 401 | No valid token, or wrong email or password |
| `SL-AUTH-403` | 403 | Logged in but not allowed (admin-only route) |
| `SL-AUTH-409` | 409 | Email already registered |
| `SL-CAT-404` / `SL-CAT-409` | 404 / 409 | Unknown SKU / SKU already exists |
| `SL-CART-404` / `SL-CART-422` | 404 / 422 | SKU not in cart / empty cart or more than 20 units |
| `SL-CPN-404` / `SL-CPN-409` / `SL-CPN-422` | 404 / 409 / 422 | Unknown coupon / already applied or second coupon / expired, inactive, below minimum or used up |
| `SL-INV-409` | 409 | Not enough sellable stock |
| `SL-INV-422` | 422 | Stock adjustment would go below zero or below held units |
| `SL-ORD-404` / `SL-ORD-409` | 404 / 409 | Order not found (or not yours) / wrong status for ship or refund |
| `SL-PAY-402` | 402 | Card declined; `details.order_id` is the failed order |
| `SL-PAY-502` | 502 | Payment gateway unreachable |
| `SL-REV-403` / `SL-REV-409` | 403 / 409 | You haven't bought it / already reviewed |
| `SL-HTTP-<status>` | varies | Flask-level errors such as an unknown route (404) or wrong method (405) |
| `SL-GEN-500` | 500 | Unexpected server error (logged with the request ID) |
