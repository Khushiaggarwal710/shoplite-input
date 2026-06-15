"""Admin-only endpoints: products, stock and all orders."""

from flask import Blueprint, request
from sqlalchemy import select

from shoplite.api.helpers import json_body, require_admin
from shoplite.errors import ValidationError
from shoplite.models import Order
from shoplite.services import catalog, stock
from shoplite.utils.money import to_paise
from shoplite.utils.pagination import page_args, paginate
from shoplite.utils.validation import get_bool, get_int, get_str

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
admin_bp.before_request(require_admin)


def read_price(body: dict, required: bool) -> int | None:
    """Read 'price' (rupees as a string, e.g. "499.00") and return paise."""
    raw = get_str(body, "price", required=required, max_len=20)
    if raw is None:
        return None
    try:
        return to_paise(raw)
    except ValueError as exc:
        raise ValidationError(f"'price' {exc}", details={"field": "price"}) from None


@admin_bp.post("/products")
def create_product():
    """Create a product with optional starting stock."""
    body = json_body()
    product = catalog.create_product(
        sku=get_str(body, "sku", max_len=40),
        name=get_str(body, "name", max_len=200),
        price_paise=read_price(body, required=True),
        category_name=get_str(body, "category", max_len=80),
        description=get_str(body, "description", required=False, max_len=2000) or "",
        initial_stock=get_int(body, "stock", required=False, minimum=0) or 0,
    )
    return product.to_dict(), 201


@admin_bp.patch("/products/<sku>")
def update_product(sku: str):
    """Change a product's name, description, price or active flag."""
    body = json_body()
    product = catalog.get_product(sku, include_inactive=True)
    changes = {}
    if "name" in body:
        changes["name"] = get_str(body, "name", max_len=200)
    if "description" in body:
        changes["description"] = get_str(body, "description", required=False, max_len=2000)
    if "price" in body:
        changes["price_paise"] = read_price(body, required=True)
    if "is_active" in body:
        changes["is_active"] = get_bool(body, "is_active", default=True)
    return catalog.update_product(product, changes).to_dict()


@admin_bp.post("/inventory/<sku>")
def adjust_inventory(sku: str):
    """Restock or write off units: {"change": 10} or {"change": -2}."""
    body = json_body()
    product = catalog.get_product(sku, include_inactive=True)
    item = stock.adjust_stock(product.id, get_int(body, "change"))
    return {"sku": sku, "on_hand": item.on_hand}


@admin_bp.get("/orders")
def list_all_orders():
    """List every order, newest first; filter with ?status=."""
    page, per_page = page_args(request.args)
    stmt = select(Order).order_by(Order.created_at.desc(), Order.id.desc())
    if request.args.get("status"):
        stmt = stmt.where(Order.status == request.args["status"])
    return paginate(stmt, page, per_page, lambda order: order.to_dict())
