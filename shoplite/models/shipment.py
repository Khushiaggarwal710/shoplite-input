"""Shipments for paid orders."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.utils import clock


class Shipment(db.Model):
    """The parcel sent for an order."""

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    carrier: Mapped[str] = mapped_column(String(40))
    tracking_code: Mapped[str] = mapped_column(String(40), unique=True)
    shipped_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    order: Mapped["Order"] = relationship(back_populates="shipment")  # noqa: F821

    def to_dict(self) -> dict:
        """JSON view of the shipment."""
        return {
            "carrier": self.carrier,
            "tracking_code": self.tracking_code,
            "shipped_at": self.shipped_at.isoformat(),
        }
