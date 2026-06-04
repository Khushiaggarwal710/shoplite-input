"""All models, imported here so every table is registered."""

from shoplite.models.cart import Cart, CartItem
from shoplite.models.category import Category
from shoplite.models.inventory import InventoryItem
from shoplite.models.order import Order, OrderItem
from shoplite.models.payment import Payment
from shoplite.models.product import Product
from shoplite.models.user import AuthToken, User

__all__ = [
    "AuthToken",
    "Cart",
    "CartItem",
    "Category",
    "InventoryItem",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "User",
]
