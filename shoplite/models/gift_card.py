"""Gift cards."""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from shoplite.extensions import db
from shoplite.utils import clock


class GiftCard(db.Model):
    """A prepaid card customers spend at checkout."""

    __tablename__ = "gift_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, comment="e.g. GC-1A2B3C4D.")
    initial_paise: Mapped[int] = mapped_column(comment="Value when issued.")
    balance_paise: Mapped[int] = mapped_column(comment="Value left to spend.")
    expires_at: Mapped[datetime | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    def to_dict(self) -> dict:
        """JSON view of the gift card."""
        return {
            "code": self.code,
            "initial_paise": self.initial_paise,
            "balance_paise": self.balance_paise,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
        }
