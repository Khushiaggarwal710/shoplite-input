"""The logged-in user's cart."""

from flask import Blueprint, g

from shoplite.api.helpers import json_body, login_required
from shoplite.services import cart as cart_service
from shoplite.services.pricing import cart_summary
from shoplite.utils.validation import get_int, get_str

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


@cart_bp.get("")
@login_required
def view_cart():
    """Show the cart."""
    return cart_summary(cart_service.get_cart(g.current_user))


@cart_bp.post("/items")
@login_required
def add_item():
    """Add a product: {"sku": "...", "quantity": 1}."""
    body = json_body()
    cart = cart_service.add_item(
        g.current_user, get_str(body, "sku"),
        get_int(body, "quantity", minimum=1, maximum=cart_service.MAX_QUANTITY_PER_LINE),
    )
    return cart_summary(cart), 201


@cart_bp.put("/items/<sku>")
@login_required
def set_quantity(sku: str):
    """Change a line's quantity; 0 removes it."""
    body = json_body()
    quantity = get_int(body, "quantity", minimum=0, maximum=cart_service.MAX_QUANTITY_PER_LINE)
    return cart_summary(cart_service.set_quantity(g.current_user, sku, quantity))


@cart_bp.delete("/items/<sku>")
@login_required
def remove_item(sku: str):
    """Remove a line from the cart."""
    return cart_summary(cart_service.set_quantity(g.current_user, sku, 0))
