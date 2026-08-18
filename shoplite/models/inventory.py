"""Stock levels and the reservation ledger."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shoplite.extensions import db
from shoplite.utils import clock

RESERVATION_HELD = "held"
RESERVATION_COMMITTED = "committed"
RESERVATION_RELEASED = "released"


class InventoryItem(db.Model):
    """How many units of one product are in the warehouse, and how many are held."""

    __tablename__ = "inventory_items"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    on_hand: Mapped[int] = mapped_column(default=0, comment="Units physically in stock.")
    reserved: Mapped[int] = mapped_column(
        default=0, comment="Units held for orders awaiting payment. Sellable = on_hand - reserved."
    )
    updated_at: Mapped[datetime] = mapped_column(default=clock.utcnow, onupdate=clock.utcnow)


class ReservationEntry(db.Model):
    """Units of one product held for one order until it is paid or the hold expires."""

    __tablename__ = "inv_reservation_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    quantity: Mapped[int]
    status: Mapped[str] = mapped_column(
        String(12), default=RESERVATION_HELD, index=True,
        comment="held (awaiting payment), committed (sold) or released (returned to stock).",
    )
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        comment="A held entry past this time is released by release_stale_reservations()."
    )
