"""Product reviews."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.models.user import User
from shoplite.utils import clock


class Review(db.Model):
    """A customer's rating and comment on a product they bought."""

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("product_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(comment="1 to 5 stars.")
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    author: Mapped[User] = relationship()

    def to_dict(self) -> dict:
        """JSON view of the review."""
        return {
            "id": self.id,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "author": self.author.name,
            "created_at": self.created_at.isoformat(),
        }
