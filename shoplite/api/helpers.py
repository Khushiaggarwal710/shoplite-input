"""Request helpers shared by the blueprints: JSON body and login checks."""

from functools import wraps

from flask import g, request

from shoplite.errors import Forbidden, Unauthorized
from shoplite.models import User
from shoplite.services import auth as auth_service
from shoplite.utils.validation import require_object


def json_body() -> dict:
    """Return the request's JSON object, or raise a 422."""
    return require_object(request.get_json(silent=True))


def bearer_token() -> str | None:
    """Read the token from 'Authorization: Bearer <token>'."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def load_current_user() -> User:
    """Find the logged-in user and store it on g, or raise a 401."""
    token = bearer_token()
    user = auth_service.user_for_token(token) if token else None
    if user is None:
        raise Unauthorized("log in first: send 'Authorization: Bearer <token>'")
    g.current_user = user
    return user


def login_required(view):
    """Decorator: the view needs a logged-in user."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        """Load the user, then run the view."""
        load_current_user()
        return view(*args, **kwargs)

    return wrapper


def require_admin() -> None:
    """Raise unless the logged-in user is an admin (used in before_request)."""
    if not load_current_user().is_admin:
        raise Forbidden("admins only")
