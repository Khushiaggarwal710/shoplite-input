"""Price a cart: subtotal, coupon discount, shipping and total."""

from dataclasses import dataclass, field

from shoplite.models import Cart, CartCoupon, Coupon
from shoplite.models.coupon import KIND_PERCENT
from shoplite.services import coupons, shipping
from shoplite.services.cart import cart_subtotal


@dataclass
class PriceQuote:
    """Every amount needed to show a cart or charge an order, in paise."""

    subtotal_paise: int
    discount_paise: int
    shipping_paise: int
    total_paise: int
    discounts: list[tuple[Coupon, int]] = field(default_factory=list)


def quote_cart(cart: Cart, pincode: str | None = None) -> PriceQuote:
    """Work out what this cart costs right now."""
    subtotal = cart_subtotal(cart)
    discounts = stack_discounts(cart.coupons, subtotal)
    discount = min(sum(amount for _, amount in discounts), subtotal)
    shipping_paise = shipping.shipping_rate_for(subtotal - discount, pincode) if cart.items else 0
    return PriceQuote(subtotal, discount, shipping_paise,
                      subtotal - discount + shipping_paise, discounts)


# Percent coupons apply to the full subtotal first; flat coupons then come off
# what is left. The order the customer applied them in doesn't matter.
def stack_discounts(applied: list[CartCoupon], subtotal_paise: int) -> list[tuple[Coupon, int]]:
    ordered = sorted(applied, key=lambda a: 0 if a.coupon.kind == KIND_PERCENT else 1)
    remaining = subtotal_paise
    discounts = []
    for entry in ordered:
        amount = coupons.coupon_discount(entry.coupon, remaining)
        discounts.append((entry.coupon, amount))
        remaining -= amount
    return discounts


def cart_summary(cart: Cart) -> dict:
    """JSON view of the cart with its prices."""
    quote = quote_cart(cart)
    return {
        "items": [
            {"sku": item.product.sku, "name": item.product.name, "quantity": item.quantity,
             "unit_price_paise": item.product.price_paise,
             "line_total_paise": item.product.price_paise * item.quantity}
            for item in cart.items
        ],
        "coupons": [coupon.code for coupon, _ in quote.discounts],
        "subtotal_paise": quote.subtotal_paise,
        "discount_paise": quote.discount_paise,
        "shipping_paise": quote.shipping_paise,
        "total_paise": quote.total_paise,
    }
