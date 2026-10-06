"""Coupon rules: who can use which code, and how much it takes off."""

from datetime import datetime

from sqlalchemy import func, select

from shoplite.errors import Conflict, NotFound, ValidationError
from shoplite.extensions import db
from shoplite.models import Cart, CartCoupon, Coupon, CouponRedemption, Order, User
from shoplite.models.coupon import KIND_FLAT, KIND_PERCENT
from shoplite.services.cart import cart_subtotal, get_cart
from shoplite.utils import clock
from shoplite.utils.money import percent_of

MAX_COUPONS_PER_ORDER = 2  # at most one percent and one flat coupon


def get_coupon(code: str) -> Coupon:
    """Find a coupon by code (case-insensitive) or raise NotFound."""
    coupon = db.session.scalar(select(Coupon).where(Coupon.code == code.upper()))
    if coupon is None:
        raise NotFound(f"no coupon {code.upper()}", code="SL-CPN-404")
    return coupon


def times_redeemed(coupon: Coupon) -> int:
    """How many paid orders have used this coupon."""
    return db.session.scalar(
        select(func.count()).select_from(CouponRedemption)
        .where(CouponRedemption.coupon_id == coupon.id)
    )


def check_redeemable(coupon: Coupon, subtotal_paise: int, now: datetime) -> None:
    """Raise a 422 if the coupon can't be used on this subtotal right now."""
    if not coupon.is_active:
        raise ValidationError(f"{coupon.code} is no longer active", code="SL-CPN-422")
    if coupon.expires_at is not None and coupon.expires_at <= now:
        raise ValidationError(f"{coupon.code} has expired", code="SL-CPN-422")
    if subtotal_paise < coupon.min_subtotal_paise:
        raise ValidationError(f"{coupon.code} needs a subtotal of at least "
                              f"{coupon.min_subtotal_paise} paise", code="SL-CPN-422")
    if coupon.max_redemptions is not None and times_redeemed(coupon) >= coupon.max_redemptions:
        raise ValidationError(f"{coupon.code} has been fully redeemed", code="SL-CPN-422")


def coupon_discount(coupon: Coupon, amount_paise: int) -> int:
    """Discount this coupon gives on an amount, never more than the amount."""
    if coupon.kind == KIND_PERCENT:
        return percent_of(amount_paise, coupon.value)
    return min(coupon.value, amount_paise)


def kind_already_applied(cart: Cart, kind: str) -> bool:
    """True if the cart already has a coupon of this kind."""
    return any(applied.coupon.kind == kind for applied in cart.coupons)


def apply_coupon(user: User, code: str) -> Cart:
    """Attach a coupon to the user's cart after checking it."""
    cart = get_cart(user)
    coupon = get_coupon(code)
    if any(applied.coupon_id == coupon.id for applied in cart.coupons):
        raise Conflict(f"{coupon.code} is already applied", code="SL-CPN-409")
    if len(cart.coupons) >= MAX_COUPONS_PER_ORDER or kind_already_applied(cart, coupon.kind):
        raise Conflict("an order can use one percent coupon and one flat coupon",
                       code="SL-CPN-409")
    check_redeemable(coupon, cart_subtotal(cart), clock.utcnow())
    cart.coupons.append(CartCoupon(coupon_id=coupon.id, coupon=coupon))
    db.session.commit()
    return cart


def remove_coupon(user: User, code: str) -> Cart:
    """Take a coupon off the user's cart."""
    cart = get_cart(user)
    applied = next((c for c in cart.coupons if c.coupon.code == code.upper()), None)
    if applied is None:
        raise NotFound(f"{code.upper()} is not applied to your cart", code="SL-CPN-404")
    cart.coupons.remove(applied)
    db.session.commit()
    return cart


def create_coupon(code: str, kind: str, value: int, min_subtotal_paise: int = 0,
                  max_redemptions: int | None = None,
                  expires_at: datetime | None = None) -> Coupon:
    """Create a coupon (admin)."""
    if kind not in (KIND_PERCENT, KIND_FLAT):
        raise ValidationError("'kind' must be 'percent' or 'flat'", details={"field": "kind"})
    if kind == KIND_PERCENT and not 1 <= value <= 100:
        raise ValidationError("percent coupons need a value from 1 to 100",
                              details={"field": "value"})
    if db.session.scalar(select(Coupon).where(Coupon.code == code.upper())):
        raise Conflict(f"coupon {code.upper()} already exists", code="SL-CPN-409")
    coupon = Coupon(code=code.upper(), kind=kind, value=value, expires_at=expires_at,
                    min_subtotal_paise=min_subtotal_paise, max_redemptions=max_redemptions)
    db.session.add(coupon)
    db.session.commit()
    return coupon


def record_redemptions(order: Order, discounts: list[tuple[Coupon, int]]) -> None:
    """Log each coupon used on a paid order (the caller commits)."""
    for coupon, discount_paise in discounts:
        db.session.add(CouponRedemption(coupon_id=coupon.id, order_id=order.id,
                                        user_id=order.user_id, discount_paise=discount_paise))
