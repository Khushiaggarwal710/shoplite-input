"""The shopping cart."""

from sqlalchemy import select

from shoplite.errors import NotFound, ValidationError
from shoplite.extensions import db
from shoplite.models import Cart, CartItem, User
from shoplite.services.catalog import get_product

MAX_QUANTITY_PER_LINE = 20


def get_cart(user: User) -> Cart:
    """Return the user's cart, creating an empty one if needed."""
    cart = db.session.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()
    return cart


def find_line(cart: Cart, sku: str) -> CartItem | None:
    """Find the cart line for a SKU."""
    return next((item for item in cart.items if item.product.sku == sku), None)


def add_item(user: User, sku: str, quantity: int) -> Cart:
    """Add units of a product, merging with an existing line."""
    cart = get_cart(user)
    product = get_product(sku)
    line = find_line(cart, sku)
    new_quantity = quantity + (line.quantity if line else 0)
    if new_quantity > MAX_QUANTITY_PER_LINE:
        raise ValidationError(f"at most {MAX_QUANTITY_PER_LINE} units per product",
                              code="SL-CART-422")
    if line:
        line.quantity = new_quantity
    else:
        cart.items.append(CartItem(product_id=product.id, quantity=quantity, product=product))
    db.session.commit()
    return cart


def set_quantity(user: User, sku: str, quantity: int) -> Cart:
    """Set a line's quantity; 0 removes the line."""
    cart = get_cart(user)
    line = find_line(cart, sku)
    if line is None:
        raise NotFound(f"{sku} is not in your cart", code="SL-CART-404")
    if quantity == 0:
        cart.items.remove(line)
    else:
        line.quantity = quantity
    db.session.commit()
    return cart


def clear_cart(cart: Cart) -> None:
    """Empty the cart and its coupons (the caller commits)."""
    cart.items.clear()
    cart.coupons.clear()


def cart_subtotal(cart: Cart) -> int:
    """Sum of price x quantity for every line, in paise."""
    return sum(item.product.price_paise * item.quantity for item in cart.items)
