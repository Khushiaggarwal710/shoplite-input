"""Product categories."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from shoplite.extensions import db


class Category(db.Model):
    """A group of products, e.g. Kitchen."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(
        String(80), unique=True, comment="URL-safe name, e.g. 'home-kitchen'."
    )

    def to_dict(self) -> dict:
        """JSON view of the category."""
        return {"id": self.id, "name": self.name, "slug": self.slug}
