# Changelog

All notable changes to ShopLite are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

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
