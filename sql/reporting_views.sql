-- Reporting views for analysts and read-only text-to-SQL.
-- scripts/seed.py creates them; they are not part of the Alembic migrations.
-- Amounts are integer paise. Only paid and shipped orders count as sales.

DROP VIEW IF EXISTS daily_sales;
CREATE VIEW daily_sales AS
SELECT DATE(created_at)     AS sale_date,
       COUNT(*)             AS orders,
       SUM(total_paise)     AS revenue_paise,
       SUM(discount_paise)  AS discounts_paise,
       SUM(shipping_paise)  AS shipping_paise
FROM orders
WHERE status IN ('paid', 'shipped')
GROUP BY DATE(created_at);

DROP VIEW IF EXISTS product_sales;
CREATE VIEW product_sales AS
SELECT p.sku,
       p.name,
       c.name                                AS category,
       SUM(oi.quantity)                      AS units_sold,
       SUM(oi.quantity * oi.unit_price_paise) AS revenue_paise
FROM order_items AS oi
JOIN orders     AS o ON o.id = oi.order_id
JOIN products   AS p ON p.id = oi.product_id
JOIN categories AS c ON c.id = p.category_id
WHERE o.status IN ('paid', 'shipped')
GROUP BY p.id;

DROP VIEW IF EXISTS coupon_performance;
CREATE VIEW coupon_performance AS
SELECT cp.code,
       cp.kind,
       COUNT(r.id)                       AS redemptions,
       COALESCE(SUM(r.discount_paise), 0) AS total_discount_paise
FROM coupons AS cp
LEFT JOIN coupon_redemption_log AS r ON r.coupon_id = cp.id
GROUP BY cp.id;
