"""Stock levels."""

from sqlalchemy import select

from shoplite.errors import ValidationError
from shoplite.extensions import db
from shoplite.models import InventoryItem


def get_inventory(product_id: int) -> InventoryItem:
    """Return the inventory row for a product."""
    return db.session.scalar(select(InventoryItem).where(InventoryItem.product_id == product_id))


def available_units(product_id: int) -> int:
    """Units that can still be sold."""
    return get_inventory(product_id).on_hand


def take_stock(product_id: int, quantity: int) -> None:
    """Remove sold units from stock (called after payment succeeds)."""
    get_inventory(product_id).on_hand -= quantity


def adjust_stock(product_id: int, change: int) -> InventoryItem:
    """Add or remove units by hand (admin restock or write-off)."""
    item = get_inventory(product_id)
    if item.on_hand + change < 0:
        raise ValidationError("stock cannot go below zero", code="SL-INV-422")
    item.on_hand += change
    db.session.commit()
    return item
