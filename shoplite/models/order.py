"""Orders and their line items."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.models.product import Product
from shoplite.models.user import User
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
    discount_paise: Mapped[int] = mapped_column(default=0, comment="Total coupon discount.")
    shipping_paise: Mapped[int] = mapped_column(default=0, comment="Shipping charge.")
    total_paise: Mapped[int] = mapped_column(
        comment="Amount charged: subtotal - discount + shipping."
    )
    gift_card_id: Mapped[int | None] = mapped_column(ForeignKey("gift_cards.id"))
    gift_card_paise: Mapped[int] = mapped_column(
        default=0, comment="Part of the total paid from a gift card; the rest goes to the card."
    )
    shipping_pincode: Mapped[str | None] = mapped_column(
        String(6), comment="6-digit Indian postal code of the delivery address."
    )
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow, index=True)
    paid_at: Mapped[datetime | None]

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.id"
    )
    shipment: Mapped["Shipment | None"] = relationship(back_populates="order")  # noqa: F821
    user: Mapped[User] = relationship()

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
            "discount_paise": self.discount_paise,
            "shipping_paise": self.shipping_paise,
            "total_paise": self.total_paise,
            "gift_card_paise": self.gift_card_paise,
            "shipping_pincode": self.shipping_pincode,
            "created_at": self.created_at.isoformat(),
            "items": [item.to_dict() for item in self.items],
            "shipment": self.shipment.to_dict() if self.shipment else None,
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
