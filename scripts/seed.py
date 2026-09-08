"""Fill a new database with the same synthetic shop data every time.

Usage: uv run python scripts/seed.py   (writes instance/shoplite.db unless SHOPLITE_DB_URL is set)
"""

import csv
import hashlib
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask_migrate import upgrade
from sqlalchemy import select

from shoplite import create_app
from shoplite.extensions import db
from shoplite.models import (
    Category,
    Coupon,
    CouponRedemption,
    InventoryItem,
    Order,
    OrderItem,
    Payment,
    Product,
    ReservationEntry,
    Review,
    Shipment,
    User,
)
from shoplite.payments.gateway import make_ref
from shoplite.services.auth import hash_password
from shoplite.services.catalog import slugify
from shoplite.services.shipping import FLAT_RATE_PAISE, FREE_SHIPPING_FROM_PAISE
from shoplite.utils.ids import order_number
from shoplite.utils.money import percent_of, to_paise

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_CSV = ROOT / "fixtures" / "products.csv"
VIEWS_SQL = ROOT / "sql" / "reporting_views.sql"

RANDOM_SEED = 2026
ORDER_COUNT = 200
FIRST_ORDER_AT = datetime(2026, 5, 1, 9, 0)
LAST_ORDER_AT = datetime(2026, 11, 10, 21, 0)
DATA_AS_OF = datetime(2026, 11, 11, 0, 0)
DEMO_PASSWORD = "shoplite-demo-1"
CARRIERS = ["BlueDart", "Delhivery", "DTDC", "Ekart"]
PINCODES = ["560001", "110001", "400001", "600002", "700001", "500001", "411001", "380001"]
CUSTOMER_NAMES = [
    "Aarav Sharma", "Diya Patel", "Vivaan Reddy", "Ananya Iyer", "Kabir Singh",
    "Ishita Banerjee", "Arjun Nair", "Meher Kapoor", "Reyansh Gupta", "Saanvi Joshi",
    "Vihaan Menon", "Kiara Desai", "Advait Kulkarni", "Myra Chatterjee", "Aditya Rao",
    "Navya Pillai", "Rohan Mehta", "Tara Verma", "Dhruv Bhat", "Zoya Qureshi",
]
REVIEW_TITLES = {
    5: ["Excellent", "Worth every rupee", "Exactly as described"],
    4: ["Good value", "Happy with it", "Does the job well"],
    3: ["Okay", "Average quality", "Fine for the price"],
    2: ["Not great", "Expected better"],
    1: ["Disappointed", "Stopped working"],
}
COUPONS = [
    # code, kind, value, min subtotal (paise), max redemptions, expires at
    ("WELCOME10", "percent", 10, 0, None, None),
    ("FLAT200", "flat", 20_000, 149_900, None, None),
    ("MONSOON5", "percent", 5, 0, None, datetime(2026, 8, 31, 23, 59)),
    ("DIWALI15", "percent", 15, 99_900, 60, datetime(2026, 11, 15, 23, 59)),
    ("SHIPFREE", "flat", 4_900, 0, 40, None),
]


def fixed_salt(email: str) -> str:
    """A salt derived from the email, so the seeded hashes are the same every run."""
    return hashlib.sha256(email.encode()).hexdigest()[:16]


def add_user(email: str, name: str, role: str, iterations: int, created_at: datetime) -> User:
    """Insert one user with the demo password."""
    user = User(email=email, name=name, role=role, created_at=created_at,
                password_hash=hash_password(DEMO_PASSWORD, iterations, fixed_salt(email)))
    db.session.add(user)
    return user


def seed_users(iterations: int) -> list[User]:
    """Insert the admin and 20 customers; returns the customers."""
    joined = datetime(2026, 4, 20, 10, 0)
    add_user("admin@shoplite.example", "ShopLite Admin", "admin", iterations, joined)
    customers = []
    for i, name in enumerate(CUSTOMER_NAMES):
        email = name.lower().replace(" ", ".") + "@example.com"
        customers.append(add_user(email, name, "customer", iterations,
                                  joined + timedelta(days=i)))
    db.session.flush()
    return customers


def seed_products() -> tuple[list[Product], dict[int, int]]:
    """Insert categories and products from the CSV; returns products and starting stock."""
    products, stock = [], {}
    categories: dict[str, Category] = {}
    with PRODUCTS_CSV.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["category"] not in categories:
                category = Category(name=row["category"], slug=slugify(row["category"]))
                db.session.add(category)
                db.session.flush()
                categories[row["category"]] = category
            product = Product(sku=row["sku"], name=row["name"], description=row["description"],
                              price_paise=to_paise(row["price"]), is_active=True,
                              category_id=categories[row["category"]].id,
                              created_at=datetime(2026, 4, 15, 9, 0))
            db.session.add(product)
            db.session.flush()
            products.append(product)
            stock[product.id] = int(row["stock"])
    return products, stock


def seed_coupons() -> list[Coupon]:
    """Insert the demo coupons."""
    coupons = [Coupon(code=code, kind=kind, value=value, min_subtotal_paise=minimum,
                      max_redemptions=limit, expires_at=expires, is_active=True,
                      created_at=datetime(2026, 4, 25, 9, 0))
               for code, kind, value, minimum, limit, expires in COUPONS]
    db.session.add_all(coupons)
    db.session.flush()
    return coupons


def pick_coupon(rng: random.Random, coupons: list[Coupon], subtotal: int, at: datetime,
                used: dict[int, int]) -> Coupon | None:
    """Pick a coupon that was valid for this order, or None (75% of orders use none)."""
    if rng.random() > 0.25:
        return None
    valid = [c for c in coupons
             if subtotal >= c.min_subtotal_paise
             and (c.expires_at is None or at < c.expires_at)
             and (c.max_redemptions is None or used[c.id] < c.max_redemptions)]
    return rng.choice(valid) if valid else None


def pick_status(rng: random.Random, at: datetime) -> str:
    """Pick an order status: about 12% failed, 5% refunded, the rest paid or shipped."""
    roll = rng.random()
    if roll < 0.12:
        return "payment_failed"
    if roll < 0.17:
        return "refunded"
    if at < DATA_AS_OF - timedelta(days=7) and rng.random() < 0.9:
        return "shipped"
    return "paid"


def seed_orders(rng: random.Random, customers: list[User], products: list[Product],
                coupons: list[Coupon], stock: dict[int, int]) -> list[Order]:
    """Insert 200 orders with items, payments, coupons, stock movements and shipments."""
    span = int((LAST_ORDER_AT - FIRST_ORDER_AT).total_seconds())
    times = sorted(FIRST_ORDER_AT + timedelta(seconds=rng.randrange(span))
                   for _ in range(ORDER_COUNT))
    used = {coupon.id: 0 for coupon in coupons}
    orders = []
    for at in times:
        lines = [(product, rng.randint(1, 3))
                 for product in rng.sample(products, rng.randint(1, 3))
                 if stock[product.id] >= 3]
        if not lines:
            continue
        status = pick_status(rng, at)
        subtotal = sum(product.price_paise * qty for product, qty in lines)
        coupon = None if status == "payment_failed" else pick_coupon(rng, coupons, subtotal,
                                                                     at, used)
        discount = 0
        if coupon:
            raw = (percent_of(subtotal, coupon.value) if coupon.kind == "percent"
                   else coupon.value)
            discount = min(raw, subtotal)
        shipping = 0 if subtotal - discount >= FREE_SHIPPING_FROM_PAISE else FLAT_RATE_PAISE
        order = Order(user_id=rng.choice(customers).id, status=status, created_at=at,
                      subtotal_paise=subtotal, discount_paise=discount, shipping_paise=shipping,
                      total_paise=subtotal - discount + shipping,
                      shipping_pincode=rng.choice(PINCODES),
                      paid_at=None if status == "payment_failed" else at + timedelta(seconds=4))
        for product, qty in lines:
            order.items.append(OrderItem(product_id=product.id, quantity=qty,
                                         unit_price_paise=product.price_paise))
        db.session.add(order)
        db.session.flush()
        add_payment_and_stock(rng, order, lines, stock)
        if coupon:
            used[coupon.id] += 1
            db.session.add(CouponRedemption(coupon_id=coupon.id, order_id=order.id,
                                            user_id=order.user_id, discount_paise=discount,
                                            redeemed_at=order.paid_at))
        if status == "shipped":
            db.session.add(Shipment(order_id=order.id, carrier=rng.choice(CARRIERS),
                                    tracking_code=f"SLX{order.id:08d}",
                                    shipped_at=at + timedelta(days=rng.randint(1, 3))))
        orders.append(order)
    return orders


def add_payment_and_stock(rng: random.Random, order: Order, lines: list,
                          stock: dict[int, int]) -> None:
    """Insert the payment row and ledger entries, and move stock, for one order."""
    number = order_number(order.id, order.created_at)
    failed = order.status == "payment_failed"
    if failed:
        gateway_down = rng.random() < 0.25
        db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                               status="error" if gateway_down else "declined",
                               error_code="SL-PAY-502" if gateway_down else "SL-PAY-402",
                               created_at=order.created_at))
    else:
        db.session.add(Payment(order_id=order.id, amount_paise=order.total_paise,
                               status="refunded" if order.status == "refunded" else "succeeded",
                               gateway_ref=make_ref("ch", number), created_at=order.created_at))
    for product, qty in lines:
        db.session.add(ReservationEntry(
            product_id=product.id, order_id=order.id, quantity=qty,
            status="released" if failed else "committed", created_at=order.created_at,
            expires_at=order.created_at + timedelta(minutes=15)))
        if order.status in ("paid", "shipped"):
            stock[product.id] -= qty  # refunded and failed orders leave stock unchanged


def seed_reviews(rng: random.Random, orders: list[Order]) -> int:
    """Insert reviews from about a third of the buyers; returns how many."""
    seen = set()
    count = 0
    for order in orders:
        if order.status not in ("paid", "shipped") or rng.random() > 0.35:
            continue
        item = rng.choice(order.items)
        if (order.user_id, item.product_id) in seen:
            continue
        seen.add((order.user_id, item.product_id))
        rating = rng.choices([5, 4, 3, 2, 1], weights=[45, 30, 12, 8, 5])[0]
        db.session.add(Review(product_id=item.product_id, user_id=order.user_id, rating=rating,
                              title=rng.choice(REVIEW_TITLES[rating]), body="",
                              created_at=order.created_at + timedelta(days=rng.randint(4, 20))))
        count += 1
    return count


def seed_inventory(stock: dict[int, int]) -> None:
    """Insert the final stock level for every product."""
    for product_id, on_hand in stock.items():
        db.session.add(InventoryItem(product_id=product_id, on_hand=on_hand, reserved=0,
                                     updated_at=DATA_AS_OF))


def main() -> int:
    """Build the schema, refuse if data exists, then insert everything."""
    app = create_app()
    with app.app_context():
        upgrade()
        if db.session.scalar(select(Product).limit(1)):
            print("Database already has data. Delete it first, e.g. rm instance/shoplite.db")
            return 1
        rng = random.Random(RANDOM_SEED)
        customers = seed_users(app.config["SHOPLITE_PASSWORD_ITERATIONS"])
        products, stock = seed_products()
        coupons = seed_coupons()
        orders = seed_orders(rng, customers, products, coupons, stock)
        reviews = seed_reviews(rng, orders)
        seed_inventory(stock)
        db.session.commit()
        db.session.connection().connection.driver_connection.executescript(
            VIEWS_SQL.read_text())
        db.session.commit()
        print(f"Seeded {len(customers)} customers, {len(products)} products, "
              f"{len(orders)} orders, {reviews} reviews into {db.engine.url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
