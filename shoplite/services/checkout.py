"""Turn a cart into a paid order."""

from flask import current_app

from shoplite import faults, observability
from shoplite.errors import OutOfStock, PaymentDeclined, PaymentGatewayError, ValidationError
from shoplite.extensions import db
from shoplite.models import Cart, Order, OrderItem, Payment, User
from shoplite.models.order import STATUS_PAID, STATUS_PAYMENT_FAILED
from shoplite.models.payment import PAYMENT_DECLINED, PAYMENT_ERROR, PAYMENT_SUCCEEDED
from shoplite.payments import gateway
from shoplite.services import cart as cart_service
from shoplite.services import coupons, shipping, stock
from shoplite.services.pricing import PriceQuote, quote_cart
from shoplite.utils import clock


def create_order(user: User, cart: Cart, shipping_pincode: str) -> tuple[Order, PriceQuote]:
    """Build an unpaid order from the cart's lines and current prices."""
    quote = quote_cart(cart, shipping_pincode)
    order = Order(user_id=user.id, subtotal_paise=quote.subtotal_paise,
                  discount_paise=quote.discount_paise, shipping_paise=quote.shipping_paise,
                  total_paise=quote.total_paise, shipping_pincode=shipping_pincode)
    for item in cart.items:
        order.items.append(OrderItem(product_id=item.product_id, quantity=item.quantity,
                                     unit_price_paise=item.product.price_paise,
                                     product=item.product))
    db.session.add(order)
    db.session.flush()
    return order, quote


def record_failed_payment(order: Order, status: str, error_code: str, outcome: str) -> None:
    """Mark the order failed and save the payment attempt."""
    stock.release_order_holds(order)
    order.status = STATUS_PAYMENT_FAILED
    db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                           status=status, error_code=error_code))
    db.session.commit()
    observability.count("shoplite_payments_total", status=status)
    observability.count("shoplite_checkouts_total", outcome=outcome)


def checkout(user: User, payment_token: str, shipping_pincode: str) -> Order:
    """Hold stock, create the order, charge the card, then commit the stock."""
    shipping.validate_pincode(shipping_pincode)
    cart = cart_service.get_cart(user)
    if not cart.items:
        raise ValidationError("your cart is empty", code="SL-CART-422")

    # Coupons were checked when applied, but may have expired since.
    subtotal = cart_service.cart_subtotal(cart)
    for applied in cart.coupons:
        coupons.check_redeemable(applied.coupon, subtotal, clock.utcnow())

    stock.release_stale_reservations()
    order, quote = create_order(user, cart, shipping_pincode)
    try:
        stock.reserve_for_order(order)
    except OutOfStock:
        db.session.rollback()
        observability.count("shoplite_checkouts_total", outcome="out_of_stock")
        raise
    db.session.commit()

    try:
        if faults.gateway_should_fail():
            raise gateway.GatewayUnavailable("fault switch: gateway errors")
        result = gateway.charge(order.total_paise, payment_token, idempotency_key=order.number)
    except gateway.GatewayUnavailable as exc:
        current_app.logger.warning("payment gateway unavailable for order %s: %s",
                                   order.number, exc)
        record_failed_payment(order, PAYMENT_ERROR, "SL-PAY-502", "gateway_error")
        raise PaymentGatewayError("payment gateway unavailable, try again",
                                  details={"order_id": order.id}) from None

    if not result.succeeded:
        record_failed_payment(order, PAYMENT_DECLINED, result.error_code, "declined")
        raise PaymentDeclined("payment was declined", details={"order_id": order.id})

    db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                           status=PAYMENT_SUCCEEDED, gateway_ref=result.gateway_ref))
    stock.commit_reservations(order)
    coupons.record_redemptions(order, quote.discounts)
    order.status = STATUS_PAID
    order.paid_at = clock.utcnow()
    cart_service.clear_cart(cart)
    db.session.commit()
    observability.count("shoplite_payments_total", status=PAYMENT_SUCCEEDED)
    observability.count("shoplite_checkouts_total", outcome="paid")
    current_app.logger.info("order paid", extra={"fields": {
        "order_number": order.number, "total_paise": order.total_paise}})
    return order
