"""Product reviews: only customers who bought a product can review it."""

from sqlalchemy import Select, func, select

from shoplite.errors import Conflict, Forbidden
from shoplite.extensions import db
from shoplite.models import Order, OrderItem, Product, Review, User
from shoplite.models.order import STATUS_PAID, STATUS_SHIPPED


def has_bought(user: User, product: Product) -> bool:
    """True if the user has a paid or shipped order containing the product."""
    stmt = (select(OrderItem.id).join(Order)
            .where(Order.user_id == user.id, OrderItem.product_id == product.id,
                   Order.status.in_([STATUS_PAID, STATUS_SHIPPED]))
            .limit(1))
    return db.session.scalar(stmt) is not None


def add_review(user: User, product: Product, rating: int, title: str, body: str) -> Review:
    """Save a review; one per customer per product."""
    if not has_bought(user, product):
        raise Forbidden("you can only review products you have bought", code="SL-REV-403")
    existing = db.session.scalar(select(Review).where(
        Review.product_id == product.id, Review.user_id == user.id))
    if existing:
        raise Conflict("you have already reviewed this product", code="SL-REV-409")
    review = Review(product_id=product.id, user_id=user.id, rating=rating, title=title, body=body)
    db.session.add(review)
    db.session.commit()
    return review


def review_query(product: Product) -> Select:
    """Reviews for a product, newest first."""
    return (select(Review).where(Review.product_id == product.id)
            .order_by(Review.created_at.desc(), Review.id.desc()))


def rating_summary(product: Product) -> dict:
    """Average rating and review count."""
    count, average = db.session.execute(
        select(func.count(Review.id), func.avg(Review.rating))
        .where(Review.product_id == product.id)).one()
    return {"count": count, "average": round(average, 2) if average is not None else None}
