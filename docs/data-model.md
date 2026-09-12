# Data model

SQLite, managed by Alembic (`migrations/versions/`). Amounts are integer paise. Times are UTC.

| Table | Holds | Key columns |
|---|---|---|
| `users` | Customers and admins | `email` (unique, lower-case), `role` |
| `auth_tokens` | Login tokens | `token_hash` (SHA-256; raw tokens are never stored), `expires_at` |
| `categories` | Product groups | `slug` |
| `products` | The catalog | `sku` (unique), `price_paise`, `is_active` |
| `inventory_items` | Stock per product | `on_hand`, `reserved`; sellable = `on_hand - reserved` |
| `inv_reservation_ledger` | Stock held per order line | `status`: `held` → `committed` (paid) or `released` (expired) |
| `carts` / `cart_items` | One cart per user | `quantity` |
| `cart_coupons` | Coupons applied to a cart | |
| `orders` | Checked-out carts | `status`, `subtotal_paise`, `discount_paise`, `shipping_paise`, `total_paise`, `shipping_pincode` |
| `order_items` | Order lines | `unit_price_paise` (price when ordered) |
| `payments` | Charge attempts | `status`, `gateway_ref`, `error_code` |
| `coupons` | Discount codes | `kind`, `value`, `min_subtotal_paise`, `max_redemptions`, `expires_at` |
| `coupon_redemption_log` | Each coupon use on a paid order | `discount_paise` |
| `reviews` | Ratings by buyers | `rating` 1–5; one per user per product |
| `shipments` | Parcels | `carrier`, `tracking_code` |

## Order statuses

`pending_payment` → `paid` → `shipped`, or `pending_payment` → `payment_failed`. Paid and shipped orders can become `refunded`.

## Schema history

| Revision | Release | Change |
|---|---|---|
| `0001` | 1.0.0 | Core tables |
| `0002` | 1.1.0 | Coupons, reviews, shipments; discount, shipping and pincode columns on `orders` |
| `0003` | 2.0.0 | `inventory_items.reserved` and `inv_reservation_ledger` |

## Reporting views

`sql/reporting_views.sql` defines `daily_sales`, `product_sales` and `coupon_performance`. `scripts/seed.py` creates them. They are not part of the migrations.

## Read-only access

For text-to-SQL and analysts, open the database read-only:

```
SHOPLITE_DB_URL="sqlite:///file:instance/shoplite.db?mode=ro&uri=true"
```

Any write then fails with `attempt to write a readonly database`.
