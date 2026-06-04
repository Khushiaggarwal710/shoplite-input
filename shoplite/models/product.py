"""Products in the catalog."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shoplite.extensions import db
from shoplite.models.category import Category
from shoplite.utils import clock


class Product(db.Model):
    """Something the shop sells."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(
        String(40), unique=True, comment="Stock-keeping unit, e.g. 'KIT-0007'. Used in URLs."
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    price_paise: Mapped[int] = mapped_column(comment="Unit price in paise (integer).")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    is_active: Mapped[bool] = mapped_column(
        default=True, comment="Hidden from the catalog when false; kept for old orders."
    )
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    category: Mapped[Category] = relationship()

    def to_dict(self) -> dict:
        """JSON view of the product."""
        return {
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price_paise": self.price_paise,
            "category": self.category.slug,
            "is_active": self.is_active,
        }
