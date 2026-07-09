"""Shipping charges and shipments."""

import re

from shoplite.errors import Conflict, ValidationError
from shoplite.extensions import db
from shoplite.models import Order, Shipment
from shoplite.models.order import STATUS_PAID, STATUS_SHIPPED
from shoplite.notifications.email import send_email

FLAT_RATE_PAISE = 4_900  # ₹49
FREE_SHIPPING_FROM_PAISE = 99_900  # free on ₹999 and above, after discounts
PINCODE_PATTERN = re.compile(r"[1-9][0-9]{5}")


def validate_pincode(pincode: str) -> str:
    """Check a 6-digit Indian postal code."""
    if not PINCODE_PATTERN.fullmatch(pincode):
        raise ValidationError("'shipping_pincode' must be a 6-digit PIN code",
                              details={"field": "shipping_pincode"})
    return pincode


def shipping_rate_for(amount_paise: int, pincode: str) -> int:
    """Shipping charge for an order of this value (same rate for every pincode)."""
    if amount_paise >= FREE_SHIPPING_FROM_PAISE:
        return 0
    return FLAT_RATE_PAISE


def ship_order(order: Order, carrier: str) -> Shipment:
    """Record the shipment for a paid order and email the customer."""
    if order.status != STATUS_PAID:
        raise Conflict(f"only paid orders can be shipped (status is {order.status})",
                       code="SL-ORD-409")
    shipment = Shipment(order_id=order.id, carrier=carrier,
                        tracking_code=f"SLX{order.id:08d}")
    order.status = STATUS_SHIPPED
    db.session.add(shipment)
    db.session.commit()
    send_email(order.user.email, f"Order {order.number} has shipped",
               f"Your parcel is with {carrier}. Tracking code: {shipment.tracking_code}.")
    return shipment
