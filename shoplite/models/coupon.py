"""Coupons and the log of every redemption."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shoplite.extensions import db
from shoplite.utils import clock

KIND_PERCENT = "percent"
KIND_FLAT = "flat"


class Coupon(db.Model):
    """A discount code."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(32), unique=True, comment="Upper-case code, e.g. DIWALI10."
    )
    kind: Mapped[str] = mapped_column(
        String(10), comment="'percent' (value is a percentage) or 'flat' (value is paise)."
    )
    value: Mapped[int] = mapped_column(comment="Percent off, or paise off for flat coupons.")
    min_subtotal_paise: Mapped[int] = mapped_column(
        default=0, comment="Cart subtotal needed before the coupon applies."
    )
    max_redemptions: Mapped[int | None] = mapped_column(
        comment="Total uses allowed across all customers; NULL means unlimited."
    )
    expires_at: Mapped[datetime | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    def to_dict(self) -> dict:
        """JSON view of the coupon."""
        return {
            "code": self.code,
            "kind": self.kind,
            "value": self.value,
            "min_subtotal_paise": self.min_subtotal_paise,
            "max_redemptions": self.max_redemptions,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
        }


class CouponRedemption(db.Model):
    """One use of a coupon on a paid order."""

    __tablename__ = "coupon_redemption_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    discount_paise: Mapped[int] = mapped_column(comment="Discount this coupon gave on this order.")
    redeemed_at: Mapped[datetime] = mapped_column(default=clock.utcnow)
