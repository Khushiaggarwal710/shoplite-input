"""Turn a cart into a paid order."""

from flask import current_app

from shoplite.errors import OutOfStock, PaymentDeclined, PaymentGatewayError, ValidationError
from shoplite.extensions import db
from shoplite.models import Order, OrderItem, Payment, User
from shoplite.models.order import STATUS_PAID, STATUS_PAYMENT_FAILED
from shoplite.models.payment import PAYMENT_DECLINED, PAYMENT_ERROR, PAYMENT_SUCCEEDED
from shoplite.payments import gateway
from shoplite.services import cart as cart_service
from shoplite.services import stock
from shoplite.utils import clock


def checkout(user: User, payment_token: str) -> Order:
    """Check stock, create the order, charge the card and take the stock."""
    cart = cart_service.get_cart(user)
    if not cart.items:
        raise ValidationError("your cart is empty", code="SL-CART-422")
    for item in cart.items:
        if stock.available_units(item.product_id) < item.quantity:
            raise OutOfStock(f"only {stock.available_units(item.product_id)} left of "
                             f"{item.product.sku}", details={"sku": item.product.sku})

    subtotal = sum(item.product.price_paise * item.quantity for item in cart.items)
    order = Order(user_id=user.id, subtotal_paise=subtotal, total_paise=subtotal)
    for item in cart.items:
        order.items.append(OrderItem(product_id=item.product_id, quantity=item.quantity,
                                     unit_price_paise=item.product.price_paise))
    db.session.add(order)
    db.session.flush()

    try:
        result = gateway.charge(order.total_paise, payment_token, idempotency_key=order.number)
    except gateway.GatewayUnavailable:
        current_app.logger.warning("payment gateway unavailable for order %s", order.number)
        order.status = STATUS_PAYMENT_FAILED
        db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                               status=PAYMENT_ERROR, error_code="SL-PAY-502"))
        db.session.commit()
        raise PaymentGatewayError("payment gateway unavailable, try again",
                                  details={"order_id": order.id}) from None

    if not result.succeeded:
        order.status = STATUS_PAYMENT_FAILED
        db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                               status=PAYMENT_DECLINED, error_code=result.error_code))
        db.session.commit()
        raise PaymentDeclined("payment was declined", details={"order_id": order.id})

    db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                           status=PAYMENT_SUCCEEDED, gateway_ref=result.gateway_ref))
    for item in order.items:
        stock.take_stock(item.product_id, item.quantity)
    order.status = STATUS_PAID
    order.paid_at = clock.utcnow()
    cart_service.clear_cart(cart)
    db.session.commit()
    return order
