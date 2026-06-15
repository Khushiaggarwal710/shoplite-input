"""Public product catalog."""

from flask import Blueprint, request

from shoplite.services import catalog
from shoplite.utils.pagination import page_args, paginate

catalog_bp = Blueprint("catalog", __name__)


@catalog_bp.get("/products")
def list_products():
    """List active products; filter with ?category= and ?q=."""
    page, per_page = page_args(request.args)
    stmt = catalog.product_query(request.args.get("category"), request.args.get("q"))
    return paginate(stmt, page, per_page, lambda product: product.to_dict())


@catalog_bp.get("/products/<sku>")
def get_product(sku: str):
    """Return one product."""
    return catalog.get_product(sku).to_dict()


@catalog_bp.get("/categories")
def list_categories():
    """List all categories."""
    return {"items": [category.to_dict() for category in catalog.list_categories()]}
