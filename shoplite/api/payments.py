"""Payment attempts for an order."""

from flask import Blueprint, g
from sqlalchemy import select

from shoplite.api.helpers import login_required
from shoplite.errors import NotFound
from shoplite.extensions import db
from shoplite.models import Order, Payment

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
