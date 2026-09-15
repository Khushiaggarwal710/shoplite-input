"""ShopLite: a small online-shop JSON API."""

import os

from flask import Flask

from shoplite import observability
from shoplite.api import register_blueprints
from shoplite.config import load_config
from shoplite.errors import register_error_handlers
from shoplite.extensions import db, migrate

__version__ = "2.0.0"


def create_app(overrides: dict | None = None) -> Flask:
    """Build and configure a ShopLite app (the application-factory pattern)."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(load_config(overrides))
    app.json.sort_keys = False  # keep fields in the order docs/api.md lists them
    os.makedirs(app.instance_path, exist_ok=True)

    observability.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    from shoplite import models  # noqa: F401  (registers every table)

    register_error_handlers(app)
    register_blueprints(app)
    return app
