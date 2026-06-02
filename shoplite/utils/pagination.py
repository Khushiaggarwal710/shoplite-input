"""Page-by-page results for list endpoints, capped at MAX_PER_PAGE."""

from collections.abc import Callable

from sqlalchemy import Select, func, select

from shoplite.extensions import db
from shoplite.utils.validation import parse_positive_int

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def page_args(args) -> tuple[int, int]:
    """Read ?page= and ?per_page= from the query string."""
    page = parse_positive_int(args.get("page", "1"), "page")
    per_page = parse_positive_int(args.get("per_page", str(DEFAULT_PER_PAGE)), "per_page")
    return page, min(per_page, MAX_PER_PAGE)


def paginate(stmt: Select, page: int, per_page: int, serialize: Callable) -> dict:
    """Run one page of a query and return items plus paging info."""
    total = db.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.session.scalars(stmt.limit(per_page).offset((page - 1) * per_page)).all()
    return {
        "items": [serialize(row) for row in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
    }
