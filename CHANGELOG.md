# Changelog

All notable changes to ShopLite are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Two checkouts at the same moment could both take the last unit. Holds are now taken in one conditional `UPDATE`.
- A failed or timed-out payment now releases its stock hold at once, instead of after 15 minutes.

## [2.0.0] - 2026-09-15

### Added
- Stock holds: checkout reserves stock in `inv_reservation_ledger` before charging, so sellable stock is `on_hand - reserved`. Holds from failed payments expire after 15 minutes.
- Admin reports: sales summary, top products and low stock (`/reports/...`).
- Structured JSON logs with a request ID on every request (`X-Request-ID`).
- `/healthz` and a Prometheus `/metrics` endpoint.
- Fault switches for incident drills (`SHOPLITE_FAULT_*`), off by default.
- Stock sync to the shoplite-warehouse service, with a fake mode.
- Dockerfile (gunicorn), deterministic seed data and reporting views.

### Changed
- **Breaking:** stock adjustments can no longer go below the units held for orders.
- `POST /admin/inventory/<sku>` also returns `reserved`.
- Refunds return items to stock through the stock service.

## [1.1.0] - 2026-07-24

### Added
- Coupons (percent or flat), one per order, with minimum subtotal, expiry and usage limits.
- Every coupon use is logged in `coupon_redemption_log`.
- Shipping: ₹49 flat, free from ₹999 after discounts. Admins can mark orders shipped.
- Verified-buyer product reviews with an average rating.
- Admin refunds, which return items to stock.
- Email notifications (stubbed: logged, not sent).

### Changed
- Checkout now requires `shipping_pincode`.
- Cart responses include discount, shipping and total.

### Fixed
- `GET /orders/<id>` returned other customers' orders. It now returns 404.

## [1.0.0] - 2026-06-19

### Added
- Customer accounts with bearer-token login and logout.
- Product catalog with categories, search and pagination.
- Shopping cart, one per user, capped at 20 units per product.
- Checkout with stock check, fake payment gateway and order history.
- Admin endpoints for products, stock adjustments and all orders.
