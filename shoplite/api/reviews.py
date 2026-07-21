"""Product reviews."""

from flask import Blueprint, g, request

from shoplite.api.helpers import json_body, login_required
from shoplite.services import catalog, reviews
from shoplite.utils.pagination import page_args, paginate
from shoplite.utils.validation import get_int, get_str

reviews_bp = Blueprint("reviews", __name__)


@reviews_bp.get("/products/<sku>/reviews")
def list_reviews(sku: str):
    """List a product's reviews with its average rating."""
    product = catalog.get_product(sku)
    page, per_page = page_args(request.args)
    result = paginate(reviews.review_query(product), page, per_page, lambda r: r.to_dict())
    result["rating"] = reviews.rating_summary(product)
    return result


@reviews_bp.post("/products/<sku>/reviews")
@login_required
def add_review(sku: str):
    """Review a product you bought: {"rating": 5, "title": "...", "body": "..."}."""
    body = json_body()
    review = reviews.add_review(
        g.current_user, catalog.get_product(sku),
        rating=get_int(body, "rating", minimum=1, maximum=5),
        title=get_str(body, "title", max_len=120),
        body=get_str(body, "body", required=False, max_len=2000) or "",
    )
    return review.to_dict(), 201
