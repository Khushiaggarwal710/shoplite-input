"""Products and categories."""

import re

from sqlalchemy import Select, select

from shoplite.errors import Conflict, NotFound
from shoplite.extensions import db
from shoplite.models import Category, InventoryItem, Product


def slugify(name: str) -> str:
    """Turn 'Home & Kitchen' into 'home-kitchen'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def list_categories() -> list[Category]:
    """All categories, by name."""
    return db.session.scalars(select(Category).order_by(Category.name)).all()


def get_or_create_category(name: str) -> Category:
    """Find a category by name, creating it if needed."""
    category = db.session.scalar(select(Category).where(Category.name == name))
    if category is None:
        category = Category(name=name, slug=slugify(name))
        db.session.add(category)
        db.session.flush()
    return category


def product_query(category_slug: str | None = None, search: str | None = None,
                  include_inactive: bool = False) -> Select:
    """Build the product-list query with optional filters."""
    stmt = select(Product).order_by(Product.sku)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_slug:
        stmt = stmt.join(Product.category).where(Category.slug == category_slug)
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    return stmt


def get_product(sku: str, include_inactive: bool = False) -> Product:
    """Find a product by SKU or raise NotFound."""
    product = db.session.scalar(select(Product).where(Product.sku == sku))
    if product is None or (not product.is_active and not include_inactive):
        raise NotFound(f"no product with SKU {sku}", code="SL-CAT-404")
    return product


def create_product(sku: str, name: str, price_paise: int, category_name: str,
                   description: str = "", initial_stock: int = 0) -> Product:
    """Add a product and its inventory row."""
    if db.session.scalar(select(Product).where(Product.sku == sku)):
        raise Conflict(f"SKU {sku} already exists", code="SL-CAT-409")
    category = get_or_create_category(category_name)
    product = Product(sku=sku, name=name, price_paise=price_paise,
                      category_id=category.id, description=description)
    db.session.add(product)
    db.session.flush()
    db.session.add(InventoryItem(product_id=product.id, on_hand=initial_stock))
    db.session.commit()
    return product


def update_product(product: Product, changes: dict) -> Product:
    """Apply allowed field changes (name, description, price_paise, is_active)."""
    for field in ("name", "description", "price_paise", "is_active"):
        if field in changes:
            setattr(product, field, changes[field])
    db.session.commit()
    return product
