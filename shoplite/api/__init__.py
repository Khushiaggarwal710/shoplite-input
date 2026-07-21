"""Blueprint registry. Add a new blueprint to BLUEPRINTS once."""

from flask import Flask

from shoplite.api.admin import admin_bp
from shoplite.api.auth import auth_bp
from shoplite.api.cart import cart_bp
from shoplite.api.catalog import catalog_bp
from shoplite.api.coupons import coupons_bp
from shoplite.api.orders import orders_bp
from shoplite.api.payments import payments_bp
from shoplite.api.reviews import reviews_bp

BLUEPRINTS = [
    auth_bp,
    catalog_bp,
    cart_bp,
    orders_bp,
    payments_bp,
    coupons_bp,
    reviews_bp,
    admin_bp,
]


def register_blueprints(app: Flask) -> None:
    """Attach every blueprint to the app."""
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
