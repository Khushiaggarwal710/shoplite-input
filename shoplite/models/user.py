"""Customers, admins and their login tokens."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.utils import clock

ROLE_CUSTOMER = "customer"
ROLE_ADMIN = "admin"


class User(db.Model):
    """A shop account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, comment="Login identifier, stored lower-cased."
    )
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(
        String(255), comment="pbkdf2:sha256:<iterations>$<salt>$<digest>; never the password."
    )
    role: Mapped[str] = mapped_column(
        String(20), default=ROLE_CUSTOMER, comment="'customer' or 'admin'."
    )
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    @property
    def is_admin(self) -> bool:
        """True for admin accounts."""
        return self.role == ROLE_ADMIN

    def to_dict(self) -> dict:
        """Public view of the user (no password hash)."""
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


class AuthToken(db.Model):
    """A bearer token issued at login."""

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, comment="SHA-256 of the token; the raw token is never stored."
    )
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    user: Mapped[User] = relationship()
