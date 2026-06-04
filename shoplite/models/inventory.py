"""Stock levels per product."""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from shoplite.extensions import db
from shoplite.utils import clock


class InventoryItem(db.Model):
    """How many units of one product are in the warehouse."""

    __tablename__ = "inventory_items"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
    on_hand: Mapped[int] = mapped_column(default=0, comment="Units physically in stock.")
    updated_at: Mapped[datetime] = mapped_column(default=clock.utcnow, onupdate=clock.utcnow)
