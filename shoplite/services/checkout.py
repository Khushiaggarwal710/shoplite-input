"""Turn a cart into a paid order."""

from flask import current_app

from shoplite.errors import OutOfStock, PaymentDeclined, PaymentGatewayError, ValidationError
from shoplite.extensions import db
from shoplite.models import Order, OrderItem, Payment, User
from shoplite.models.order import STATUS_PAID, STATUS_PAYMENT_FAILED
from shoplite.models.payment import PAYMENT_DECLINED, PAYMENT_ERROR, PAYMENT_SUCCEEDED
from shoplite.payments import gateway
from shoplite.services import cart as cart_service
from shoplite.services import coupons, shipping, stock
from shoplite.services.pricing import quote_cart
from shoplite.utils import clock


def checkout(user: User, payment_token: str, shipping_pincode: str) -> Order:
    """Check stock and coupons, create the order, charge the card and take the stock."""
    shipping.validate_pincode(shipping_pincode)
    cart = cart_service.get_cart(user)
    if not cart.items:
        raise ValidationError("your cart is empty", code="SL-CART-422")
    for item in cart.items:
        if stock.available_units(item.product_id) < item.quantity:
            raise OutOfStock(f"only {stock.available_units(item.product_id)} left of "
                             f"{item.product.sku}", details={"sku": item.product.sku})

    # Coupons were checked when applied, but may have expired since.
    subtotal = cart_service.cart_subtotal(cart)
    for applied in cart.coupons:
        coupons.check_redeemable(applied.coupon, subtotal, clock.utcnow())
    quote = quote_cart(cart, shipping_pincode)

    order = Order(user_id=user.id, subtotal_paise=quote.subtotal_paise,
                  discount_paise=quote.discount_paise, shipping_paise=quote.shipping_paise,
                  total_paise=quote.total_paise, shipping_pincode=shipping_pincode)
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
    coupons.record_redemptions(order, quote.discounts)
    order.status = STATUS_PAID
    order.paid_at = clock.utcnow()
    cart_service.clear_cart(cart)
    db.session.commit()
    return order
