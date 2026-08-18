"""All models, imported here so every table is registered."""

from shoplite.models.cart import Cart, CartCoupon, CartItem
from shoplite.models.category import Category
from shoplite.models.coupon import Coupon, CouponRedemption
from shoplite.models.inventory import InventoryItem, ReservationEntry
from shoplite.models.order import Order, OrderItem
from shoplite.models.payment import Payment
from shoplite.models.product import Product
from shoplite.models.review import Review
from shoplite.models.shipment import Shipment
from shoplite.models.user import AuthToken, User

__all__ = [
    "AuthToken",
    "Cart",
    "CartCoupon",
    "CartItem",
    "Category",
    "Coupon",
    "CouponRedemption",
    "InventoryItem",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "ReservationEntry",
    "Review",
    "Shipment",
    "User",
]
