"""Refunds for paid or shipped orders."""

from sqlalchemy import select

from shoplite.errors import Conflict
from shoplite.extensions import db
from shoplite.models import Order, Payment
from shoplite.models.order import STATUS_PAID, STATUS_REFUNDED, STATUS_SHIPPED
from shoplite.models.payment import PAYMENT_REFUNDED, PAYMENT_SUCCEEDED
from shoplite.notifications.email import send_email
from shoplite.payments import gateway
from shoplite.services import stock


def refund_order(order: Order) -> Order:
    """Refund the full amount and put the items back in stock."""
    if order.status not in (STATUS_PAID, STATUS_SHIPPED):
        raise Conflict(f"cannot refund an order with status {order.status}", code="SL-ORD-409")
    payment = db.session.scalar(select(Payment).where(
        Payment.order_id == order.id, Payment.status == PAYMENT_SUCCEEDED))
    gateway.refund(payment.gateway_ref, payment.amount_paise)
    payment.status = PAYMENT_REFUNDED
    for item in order.items:
        stock.take_stock(item.product_id, -item.quantity)
    order.status = STATUS_REFUNDED
    db.session.commit()
    send_email(order.user.email, f"Refund for order {order.number}",
               f"We have refunded {payment.amount_paise} paise to your card.")
    return order
