"""Stock reports in SQL, using bound parameters (:name), never string formatting."""

from sqlalchemy import text

from shoplite import faults
from shoplite.extensions import db

LOW_STOCK_SQL = text("""
    SELECT p.sku, p.name, i.on_hand, i.reserved, i.on_hand - i.reserved AS sellable
    FROM inventory_items AS i
    JOIN products AS p ON p.id = i.product_id
    WHERE p.is_active = 1 AND i.on_hand - i.reserved <= :threshold
    ORDER BY sellable, p.sku
""")


def low_stock(threshold: int) -> list[dict]:
    """Active products with sellable stock at or below the threshold."""
    faults.maybe_slow_query()
    rows = db.session.execute(LOW_STOCK_SQL, {"threshold": threshold}
    return [dict(row) for row in rows.mappings()]
