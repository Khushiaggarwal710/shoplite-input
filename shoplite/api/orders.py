"""Checkout and order history."""

from flask import Blueprint, g, request
from sqlalchemy import select

from shoplite.api.helpers import json_body, login_required
from shoplite.errors import NotFound
from shoplite.extensions import db
from shoplite.models import Order
from shoplite.services.checkout import checkout
from shoplite.utils.pagination import page_args, paginate
from shoplite.utils.validation import get_str

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


@orders_bp.post("")
@login_required
def place_order():
    """Check out the cart: {"payment_token": "tok_success"}."""
    body = json_body()
    order = checkout(g.current_user, get_str(body, "payment_token"))
    return order.to_dict(), 201


@orders_bp.get("")
@login_required
def list_orders():
    """List the user's own orders, newest first."""
    page, per_page = page_args(request.args)
    stmt = (select(Order).where(Order.user_id == g.current_user.id)
            .order_by(Order.created_at.desc(), Order.id.desc()))
    return paginate(stmt, page, per_page, lambda order: order.to_dict())


@orders_bp.get("/<int:order_id>")
@login_required
def get_order(order_id: int):
    """Return one of your orders (admins can see any order)."""
    order = db.session.get(Order, order_id)
    # 404, not 403, so other users can't tell which order IDs exist.
    if order is None or (order.user_id != g.current_user.id and not g.current_user.is_admin):
        raise NotFound("order not found", code="SL-ORD-404")
    return order.to_dict()
