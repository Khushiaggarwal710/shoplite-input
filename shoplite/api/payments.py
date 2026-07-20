"""Payment attempts and refunds for an order."""

from flask import Blueprint, g
from sqlalchemy import select

from shoplite.api.helpers import login_required, require_admin
from shoplite.errors import NotFound
from shoplite.extensions import db
from shoplite.models import Order, Payment
from shoplite.services.refunds import refund_order

payments_bp = Blueprint("payments", __name__)


@payments_bp.get("/orders/<int:order_id>/payments")
@login_required
def list_payments(order_id: int):
    """List charge attempts for one of your orders."""
    order = db.session.get(Order, order_id)
    if order is None or (order.user_id != g.current_user.id and not g.current_user.is_admin):
        raise NotFound("order not found", code="SL-ORD-404")
    payments = db.session.scalars(
        select(Payment).where(Payment.order_id == order.id).order_by(Payment.id)).all()
    return {"items": [payment.to_dict() for payment in payments]}


@payments_bp.post("/orders/<int:order_id>/refund")
def refund(order_id: int):
    """Refund an order in full (admins only)."""
    require_admin()
    order = db.session.get(Order, order_id)
    if order is None:
        raise NotFound("order not found", code="SL-ORD-404")
    return refund_order(order).to_dict()
