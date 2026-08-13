"""Health check and metrics for operations."""

from flask import Blueprint, Response, current_app
from sqlalchemy import text

import shoplite
from shoplite.extensions import db
from shoplite.services import stock

ops_bp = Blueprint("ops", __name__)


@ops_bp.get("/healthz")
def healthz():
    """Report whether the app can reach its database."""
    try:
        db.session.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # any DB failure means unhealthy
        current_app.logger.exception("health check: database unreachable")
        database = "error"
    status = 200 if database == "ok" else 503
    return {"status": "ok" if status == 200 else "degraded", "version": shoplite.__version__,
            "database": database}, status


@ops_bp.get("/metrics")
def metrics():
    """Prometheus metrics in text format."""
    gauges = {"shoplite_stock_reserved_units": stock.total_reserved_units()}
    body = current_app.extensions["shoplite_metrics"].render(gauges)
    return Response(body, mimetype="text/plain; version=0.0.4")
