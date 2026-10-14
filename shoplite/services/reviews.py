"""Product reviews: only customers who bought a product can review it."""

from sqlalchemy import Select, func, select

from shoplite.errors import Conflict, Forbidden, ValidationError
from shoplite.extensions import db
from shoplite.models import Order, OrderItem, Product, Review, ReviewFlag, User
from shoplite.models.order import STATUS_PAID, STATUS_SHIPPED
from shoplite.models.review import REVIEW_HIDDEN, REVIEW_PUBLISHED

FLAGS_TO_HIDE = 3
FLAG_REASONS = ("spam", "abusive", "off_topic", "other")


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
    return (select(Review).where(Review.product_id == product.id,
                                 Review.status == REVIEW_PUBLISHED)
            .order_by(Review.created_at.desc(), Review.id.desc()))


def rating_summary(product: Product) -> dict:
    """Average rating and review count."""
    count, average = db.session.execute(
        select(func.count(Review.id), func.avg(Review.rating))
        .where(Review.product_id == product.id, Review.status == REVIEW_PUBLISHED)).one()
    return {"count": count, "average": round(average, 2) if average is not None else None}


def flag_review(review: Review, user: User, reason: str) -> Review:
    """Record a flag; the third flag hides the review."""
    if reason not in FLAG_REASONS:
        raise ValidationError(f"'reason' must be one of {', '.join(FLAG_REASONS)}",
                              details={"field": "reason"})
    if review.user_id == user.id:
        raise Forbidden("you can't flag your own review", code="SL-REV-403")
    if any(flag.user_id == user.id for flag in review.flags):
        raise Conflict("you have already flagged this review", code="SL-REV-409")
    review.flags.append(ReviewFlag(user_id=user.id, reason=reason))
    if len(review.flags) >= FLAGS_TO_HIDE:
        review.status = REVIEW_HIDDEN
    db.session.commit()
    return review


def hidden_review_query() -> Select:
    """Hidden reviews, oldest first."""
    return select(Review).where(Review.status == REVIEW_HIDDEN).order_by(Review.id)


# TODO(meera): score the text with the moderation model and hide reviews above 0.9.
# Waiting on the vendor contract, so nothing calls this yet.
def score_review_text(body: str) -> float:
    """Moderation score for review text (not implemented yet)."""
    ...
