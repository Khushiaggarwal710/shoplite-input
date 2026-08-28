"""Admin reports."""

from datetime import datetime, timedelta

from flask import Blueprint, request

from shoplite.api.helpers import require_admin
from shoplite.errors import ValidationError
from shoplite.services import reports
from shoplite.utils import clock
from shoplite.utils.validation import parse_positive_int

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")
reports_bp.before_request(require_admin)


def date_range() -> tuple[datetime, datetime]:
    """Read ?start= and ?end= (ISO dates); default is the last 30 days."""
    try:
        end = datetime.fromisoformat(request.args["end"]) if "end" in request.args \
            else clock.utcnow()
        start = datetime.fromisoformat(request.args["start"]) if "start" in request.args \
            else end - timedelta(days=30)
    except ValueError:
        raise ValidationError("'start' and 'end' must be ISO dates, e.g. 2026-10-01") from None
    if start >= end:
        raise ValidationError("'start' must be before 'end'")
    return start, end


@reports_bp.get("/sales-summary")
def sales_summary():
    """Orders, revenue and average order value for a date range."""
    return reports.sales_summary(*date_range())


@reports_bp.get("/top-products")
def top_products():
    """Best sellers for a date range; ?limit= up to 50."""
    limit = min(parse_positive_int(request.args.get("limit", "10"), "limit"), 50)
    return {"items": reports.top_products(*date_range(), limit)}


@reports_bp.get("/low-stock")
def low_stock():
    """Products with sellable stock at or below ?threshold= (default 5)."""
    threshold = parse_positive_int(request.args.get("threshold", "5"), "threshold")
    return {"items": reports.low_stock(threshold)}
