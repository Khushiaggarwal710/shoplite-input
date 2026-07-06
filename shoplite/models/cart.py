"""Shopping carts: one per user."""

from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.models.coupon import Coupon
from shoplite.models.product import Product
from shoplite.utils import clock


class Cart(db.Model):
    """A user's cart."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    updated_at: Mapped[datetime] = mapped_column(default=clock.utcnow, onupdate=clock.utcnow)

    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.id"
    )
    coupons: Mapped[list["CartCoupon"]] = relationship(
        cascade="all, delete-orphan", order_by="CartCoupon.id"
    )


class CartItem(db.Model):
    """One product line in a cart."""

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]

    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class CartCoupon(db.Model):
    """A coupon code applied to a cart, waiting for checkout."""

    __tablename__ = "cart_coupons"
    __table_args__ = (UniqueConstraint("cart_id", "coupon_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), index=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"))
    applied_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    coupon: Mapped[Coupon] = relationship()
