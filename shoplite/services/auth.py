"""Registration, password hashing and bearer tokens."""

import hashlib
import hmac
import secrets
from datetime import timedelta

from flask import current_app
from sqlalchemy import select

from shoplite.errors import Conflict, Unauthorized, ValidationError
from shoplite.extensions import db
from shoplite.models import AuthToken, User
from shoplite.models.user import ROLE_CUSTOMER
from shoplite.utils import clock
from shoplite.utils.ids import hash_token, new_token

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str, iterations: int, salt: str | None = None) -> str:
    """Hash a password with PBKDF2-SHA256 and a random salt."""
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2:sha256:{iterations}${salt}${digest.hex()}"


def verify_password(password_hash: str, password: str) -> bool:
    """Check a password against a stored hash."""
    method, salt, expected = password_hash.split("$", 2)
    iterations = int(method.split(":")[2])
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return hmac.compare_digest(digest.hex(), expected)


def register_user(email: str, name: str, password: str, role: str = ROLE_CUSTOMER) -> User:
    """Create an account; emails are unique and case-insensitive."""
    email = email.lower()
    if "@" not in email:
        raise ValidationError("'email' is not a valid email address", details={"field": "email"})
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"'password' must be at least {MIN_PASSWORD_LENGTH} characters",
            details={"field": "password"},
        )
    if db.session.scalar(select(User).where(User.email == email)):
        raise Conflict("an account with this email already exists", code="SL-AUTH-409")
    iterations = current_app.config["SHOPLITE_PASSWORD_ITERATIONS"]
    user = User(email=email, name=name, role=role,
                password_hash=hash_password(password, iterations))
    db.session.add(user)
    db.session.commit()
    return user


def login(email: str, password: str) -> str:
    """Check credentials and return a new raw bearer token."""
    user = db.session.scalar(select(User).where(User.email == email.lower()))
    # Same message for "no such user" and "wrong password", so emails can't be probed.
    if user is None or not verify_password(user.password_hash, password):
        raise Unauthorized("invalid email or password")
    raw_token = new_token()
    ttl = timedelta(hours=current_app.config["SHOPLITE_TOKEN_TTL_HOURS"])
    db.session.add(AuthToken(user_id=user.id, token_hash=hash_token(raw_token),
                             expires_at=clock.utcnow() + ttl))
    db.session.commit()
    return raw_token


def find_token(raw_token: str) -> AuthToken | None:
    """Look up a stored token by its hash."""
    return db.session.scalar(select(AuthToken).where(AuthToken.token_hash == hash_token(raw_token)))


def user_for_token(raw_token: str) -> User | None:
    """Return the user a token belongs to, or None if unknown or expired."""
    token = find_token(raw_token)
    if token is None or token.expires_at <= clock.utcnow():
        return None
    return token.user


def logout(raw_token: str) -> None:
    """Delete a token so it can't be used again."""
    token = find_token(raw_token)
    if token is not None:
        db.session.delete(token)
        db.session.commit()
