"""Admin sales and stock reports in SQL, using bound parameters (:name), never string formatting."""

from datetime import datetime

from sqlalchemy import DateTime, bindparam, text

from shoplite import faults
from shoplite.extensions import db

SALES_SUMMARY_SQL = text("""
    SELECT COUNT(*)                         AS orders,
           COALESCE(SUM(total_paise), 0)    AS revenue_paise,
           COALESCE(SUM(discount_paise), 0) AS discounts_paise,
           COALESCE(AVG(total_paise), 0)    AS average_order_paise
    FROM orders
    WHERE status IN ('paid', 'shipped')
      AND created_at >= :start AND created_at < :end
""").bindparams(bindparam("start", type_=DateTime), bindparam("end", type_=DateTime))

TOP_PRODUCTS_SQL = text("""
    SELECT p.sku, p.name,
           SUM(oi.quantity)                       AS units_sold,
           SUM(oi.quantity * oi.unit_price_paise) AS revenue_paise
    FROM order_items AS oi
    JOIN orders   AS o ON o.id = oi.order_id
    JOIN products AS p ON p.id = oi.product_id
    WHERE o.status IN ('paid', 'shipped')
      AND o.created_at >= :start AND o.created_at < :end
    GROUP BY p.id
    ORDER BY units_sold DESC, p.sku
    LIMIT :limit
""").bindparams(bindparam("start", type_=DateTime), bindparam("end", type_=DateTime))

LOW_STOCK_SQL = text("""
    SELECT p.sku, p.name, i.on_hand, i.reserved, i.on_hand - i.reserved AS sellable
    FROM inventory_items AS i
    JOIN products AS p ON p.id = i.product_id
    WHERE p.is_active = 1 AND i.on_hand - i.reserved <= :threshold
    ORDER BY sellable, p.sku
""")


def sales_summary(start: datetime, end: datetime) -> dict:
    """Orders, revenue, discounts and average order value between two dates."""
    faults.maybe_slow_query()
    row = db.session.execute(SALES_SUMMARY_SQL, {"start": start, "end": end}).mappings().one()
    return {"start": start.isoformat(), "end": end.isoformat(),
            **{key: int(value) for key, value in row.items()}}


def top_products(start: datetime, end: datetime, limit: int) -> list[dict]:
    """Best-selling products by units between two dates."""
    faults.maybe_slow_query()
    rows = db.session.execute(TOP_PRODUCTS_SQL, {"start": start, "end": end, "limit": limit})
    return [dict(row) for row in rows.mappings()]


def low_stock(threshold: int) -> list[dict]:
    """Active products with sellable stock at or below the threshold."""
    faults.maybe_slow_query()
    return [dict(row) for row in db.session.execute(LOW_STOCK_SQL, {"threshold": threshold})
            .mappings()]
