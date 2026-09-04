"""Test fixtures. The ONLY test file that may import Flask or the app factory.

Tests talk to ShopLite through the HTTP `client`, so moving the app to another
framework means rewriting this file, not the tests.
"""

import itertools
from types import SimpleNamespace

import pytest
from flask_migrate import upgrade

from shoplite import create_app
from shoplite.extensions import db
from shoplite.models.user import ROLE_ADMIN
from shoplite.services.auth import register_user
from shoplite.utils import clock

TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite://",
    "SHOPLITE_PASSWORD_ITERATIONS": 1_000,
}
PASSWORD = "correct-horse-1"


def build_app(overrides: dict | None = None):
    """Create an app on a fresh in-memory database."""
    app = create_app({**TEST_CONFIG, **(overrides or {})})
    with app.app_context():
        db.create_all()
        register_user("admin@shoplite.test", "Admin", PASSWORD, role=ROLE_ADMIN)
    return app


@pytest.fixture
def app_factory():
    """Return a function that builds a client with extra config."""

    def make_client(**overrides):
        """Build a test client with the given config overrides."""
        return build_app(overrides).test_client()

    return make_client


@pytest.fixture
def shop_with(app_factory):
    """Return a function that builds a shop with config overrides, a customer and one product."""

    def make_shop(**overrides) -> SimpleNamespace:
        """Build the shop; returns client, admin_headers, customer_headers and sku."""
        client = app_factory(**overrides)
        admin_headers = login_headers(client, "admin@shoplite.test")
        client.post("/admin/products", headers=admin_headers, json={
            "sku": "FLT-0001", "name": "Fault drill product", "price": "100.00",
            "category": "Drills", "stock": 5})
        client.post("/auth/register", json={
            "email": "drill@shoplite.test", "name": "Drill", "password": PASSWORD})
        return SimpleNamespace(client=client, admin_headers=admin_headers, sku="FLT-0001",
                               customer_headers=login_headers(client, "drill@shoplite.test"))

    return make_shop


@pytest.fixture
def client():
    """HTTP test client on an empty shop (one admin user)."""
    app = build_app()
    yield app.test_client()
    with app.app_context():
        db.session.remove()


@pytest.fixture
def migrated_db(tmp_path):
    """Build a file database with `flask db upgrade` and return its path."""
    path = tmp_path / "migrated.db"
    app = create_app({**TEST_CONFIG, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}"})
    with app.app_context():
        upgrade()
    return path


@pytest.fixture(autouse=True)
def reset_clock():
    """Put the clock back after every test."""
    yield
    clock.reset()


@pytest.fixture
def move_clock():
    """Return clock.advance so a test can move time forward."""
    return clock.advance


def login_headers(client, email: str) -> dict:
    """Log in and return the Authorization header."""
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.get_json()
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


@pytest.fixture
def admin_headers(client):
    """Auth header for the admin user."""
    return login_headers(client, "admin@shoplite.test")


@pytest.fixture
def customer(client):
    """Return a function that registers a customer and returns their auth header."""
    counter = itertools.count(1)

    def make_customer(email: str | None = None) -> dict:
        """Register a customer and log them in."""
        email = email or f"customer{next(counter)}@shoplite.test"
        response = client.post("/auth/register",
                               json={"email": email, "name": "Test Customer", "password": PASSWORD})
        assert response.status_code == 201, response.get_json()
        return login_headers(client, email)

    return make_customer


@pytest.fixture
def product(client, admin_headers):
    """Return a function that creates a product through the admin API."""
    counter = itertools.count(1)

    def make_product(sku: str | None = None, price: str = "500.00", stock: int = 10,
                     category: str = "Kitchen") -> str:
        """Create a product and return its SKU."""
        sku = sku or f"TST-{next(counter):04d}"
        response = client.post("/admin/products", headers=admin_headers, json={
            "sku": sku, "name": f"Test product {sku}", "price": price,
            "category": category, "stock": stock,
        })
        assert response.status_code == 201, response.get_json()
        return sku

    return make_product


@pytest.fixture
def buy(client):
    """Return a function that fills a cart and checks out."""

    def checkout(headers: dict, items: dict, payment_token: str = "tok_success",
                 coupon: str | None = None):
        """Add {sku: quantity} (and a coupon) to the cart and place the order."""
        for sku, quantity in items.items():
            response = client.post("/cart/items", headers=headers,
                                   json={"sku": sku, "quantity": quantity})
            assert response.status_code == 201, response.get_json()
        if coupon:
            response = client.post("/cart/coupons", headers=headers, json={"code": coupon})
            assert response.status_code == 201, response.get_json()
        return client.post("/orders", headers=headers,
                           json={"payment_token": payment_token, "shipping_pincode": "560001"})

    return checkout


@pytest.fixture
def coupon(client, admin_headers):
    """Return a function that creates a coupon through the admin API."""

    def make_coupon(code: str, kind: str = "percent", value: int = 10, **extra) -> str:
        """Create a coupon and return its code."""
        response = client.post("/coupons", headers=admin_headers,
                               json={"code": code, "kind": kind, "value": value, **extra})
        assert response.status_code == 201, response.get_json()
        return code

    return make_coupon
