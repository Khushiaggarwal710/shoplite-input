"""Orders and their line items."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.models.product import Product
from shoplite.utils import clock
from shoplite.utils.ids import order_number

STATUS_PENDING_PAYMENT = "pending_payment"
STATUS_PAID = "paid"
STATUS_PAYMENT_FAILED = "payment_failed"
STATUS_SHIPPED = "shipped"
STATUS_REFUNDED = "refunded"


class Order(db.Model):
    """A checked-out cart."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=STATUS_PENDING_PAYMENT,
        comment="pending_payment, paid, payment_failed, shipped or refunded.",
    )
    subtotal_paise: Mapped[int] = mapped_column(comment="Sum of line totals before discounts.")
    total_paise: Mapped[int] = mapped_column(comment="Amount charged to the customer.")
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow, index=True)
    paid_at: Mapped[datetime | None]

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )

    @property
    def number(self) -> str:
        """Customer-facing order number."""
        return order_number(self.id, self.created_at)

    def to_dict(self) -> dict:
        """JSON view of the order with its items."""
        return {
            "id": self.id,
            "number": self.number,
            "status": self.status,
            "subtotal_paise": self.subtotal_paise,
            "total_paise": self.total_paise,
            "created_at": self.created_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    """One product line in an order, with the price at time of purchase."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int]
    unit_price_paise: Mapped[int] = mapped_column(
        comment="Price when ordered; later price changes don't touch old orders."
    )

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

    def to_dict(self) -> dict:
        """JSON view of the line."""
        return {
            "sku": self.product.sku,
            "name": self.product.name,
            "quantity": self.quantity,
            "unit_price_paise": self.unit_price_paise,
        }
