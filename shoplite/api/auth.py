"""Register, log in, log out."""

from flask import Blueprint, g

from shoplite.api.helpers import bearer_token, json_body, login_required
from shoplite.services import auth as auth_service
from shoplite.utils.validation import get_str

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    """Create a customer account."""
    body = json_body()
    user = auth_service.register_user(
        email=get_str(body, "email"),
        name=get_str(body, "name", max_len=120),
        password=get_str(body, "password"),
    )
    return user.to_dict(), 201


@auth_bp.post("/login")
def login():
    """Exchange email and password for a bearer token."""
    body = json_body()
    token = auth_service.login(get_str(body, "email"), get_str(body, "password"))
    return {"token": token, "token_type": "Bearer"}


@auth_bp.post("/logout")
@login_required
def logout():
    """Revoke the token used for this request."""
    auth_service.logout(bearer_token())
    return "", 204


@auth_bp.get("/me")
@login_required
def me():
    """Return the logged-in user."""
    return g.current_user.to_dict()
