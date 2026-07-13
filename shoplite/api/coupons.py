"""Apply coupons to the cart; admins create them."""

from datetime import datetime

from flask import Blueprint, g
from sqlalchemy import select

from shoplite.api.helpers import json_body, login_required, require_admin
from shoplite.errors import ValidationError
from shoplite.extensions import db
from shoplite.models import Coupon
from shoplite.services import coupons
from shoplite.services.pricing import cart_summary
from shoplite.utils.validation import get_int, get_str

coupons_bp = Blueprint("coupons", __name__)


@coupons_bp.post("/cart/coupons")
@login_required
def apply_coupon():
    """Apply a coupon code to your cart: {"code": "WELCOME10"}."""
    cart = coupons.apply_coupon(g.current_user, get_str(json_body(), "code", max_len=32))
    return cart_summary(cart), 201


@coupons_bp.delete("/cart/coupons/<code>")
@login_required
def remove_coupon(code: str):
    """Remove a coupon from your cart."""
    return cart_summary(coupons.remove_coupon(g.current_user, code))


@coupons_bp.post("/coupons")
def create_coupon():
    """Create a coupon (admins only)."""
    require_admin()
    body = json_body()
    expires_raw = get_str(body, "expires_at", required=False, max_len=40)
    try:
        expires_at = datetime.fromisoformat(expires_raw) if expires_raw else None
    except ValueError:
        raise ValidationError("'expires_at' must be an ISO date-time",
                              details={"field": "expires_at"}) from None
    coupon = coupons.create_coupon(
        code=get_str(body, "code", max_len=32),
        kind=get_str(body, "kind", max_len=10),
        value=get_int(body, "value", minimum=1),
        min_subtotal_paise=get_int(body, "min_subtotal_paise", required=False, minimum=0) or 0,
        max_redemptions=get_int(body, "max_redemptions", required=False, minimum=1),
        expires_at=expires_at,
    )
    return coupon.to_dict(), 201


@coupons_bp.get("/coupons")
def list_coupons():
    """List all coupons (admins only)."""
    require_admin()
    rows = db.session.scalars(select(Coupon).order_by(Coupon.code)).all()
    return {"items": [coupon.to_dict() for coupon in rows]}
