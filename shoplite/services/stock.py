"""Stock levels and reservations (holds) in inv_reservation_ledger.

Checkout holds stock while the card is charged; failed-payment holds expire after RESERVATION_TTL.
"""

from datetime import timedelta

from sqlalchemy import select

from shoplite import faults, warehouse_client
from shoplite.errors import OutOfStock, ValidationError
from shoplite.extensions import db
from shoplite.models import InventoryItem, Order, Product, ReservationEntry
from shoplite.models.inventory import (
    RESERVATION_COMMITTED,
    RESERVATION_HELD,
    RESERVATION_RELEASED,
)
from shoplite.utils import clock

RESERVATION_TTL = timedelta(minutes=15)


def get_inventory(product_id: int) -> InventoryItem:
    """Return the inventory row for a product."""
    return db.session.scalar(select(InventoryItem).where(InventoryItem.product_id == product_id))


def available_units(product_id: int) -> int:
    """Units that can still be sold (on hand minus held)."""
    item = get_inventory(product_id)
    return item.on_hand - item.reserved


def sync_to_warehouse(product_id: int) -> None:
    """Tell the warehouse service the new on-hand count."""
    product = db.session.get(Product, product_id)
    warehouse_client.push_stock_level(product.sku, get_inventory(product_id).on_hand)


# Reads the available count, then writes the new reserved count. Two checkouts
# running at the same moment can both pass the check for the last unit.
def reserve_for_order(order: Order) -> None:
    """Hold stock for every line of an order, or raise OutOfStock."""
    expires_at = clock.utcnow() + RESERVATION_TTL
    for line in order.items:
        item = get_inventory(line.product_id)
        if item.on_hand - item.reserved < line.quantity:
            raise OutOfStock(f"only {item.on_hand - item.reserved} left of {line.product.sku}",
                             details={"sku": line.product.sku})
        item.reserved += line.quantity
        db.session.add(ReservationEntry(product_id=line.product_id, order_id=order.id,
                                        quantity=line.quantity, expires_at=expires_at))


def held_entries(order_id: int) -> list[ReservationEntry]:
    """Held ledger entries for one order."""
    return db.session.scalars(select(ReservationEntry).where(
        ReservationEntry.order_id == order_id,
        ReservationEntry.status == RESERVATION_HELD)).all()


def commit_reservations(order: Order) -> None:
    """Turn an order's holds into sales: the units leave stock."""
    for entry in held_entries(order.id):
        item = get_inventory(entry.product_id)
        item.on_hand -= entry.quantity
        item.reserved -= entry.quantity
        entry.status = RESERVATION_COMMITTED
        sync_to_warehouse(entry.product_id)


def release_entry(entry: ReservationEntry) -> None:
    """Give one hold back to sellable stock."""
    get_inventory(entry.product_id).reserved -= entry.quantity
    entry.status = RESERVATION_RELEASED


def release_stale_reservations() -> int:
    """Release holds past their expiry time; returns how many were released."""
    if faults.reservation_leak_enabled():
        return 0
    stale = db.session.scalars(select(ReservationEntry).where(
        ReservationEntry.status == RESERVATION_HELD,
        ReservationEntry.expires_at <= clock.utcnow())).all()
    for entry in stale:
        release_entry(entry)
    db.session.commit()
    return len(stale)


def total_reserved_units() -> int:
    """Units currently held across all products (for /metrics)."""
    return sum(db.session.scalars(select(InventoryItem.reserved)).all())


def return_to_stock(product_id: int, quantity: int) -> None:
    """Put refunded units back on the shelf (the caller commits)."""
    get_inventory(product_id).on_hand += quantity
    sync_to_warehouse(product_id)


def adjust_stock(product_id: int, change: int) -> InventoryItem:
    """Add or remove units by hand (admin restock or write-off)."""
    item = get_inventory(product_id)
    if item.on_hand + change < item.reserved:
        raise ValidationError("stock cannot go below zero or below the units held for orders",
                              code="SL-INV-422")
    item.on_hand += change
    db.session.commit()
    sync_to_warehouse(product_id)
    return item
