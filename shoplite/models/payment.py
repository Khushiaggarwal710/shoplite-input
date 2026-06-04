"""Payment attempts against the gateway."""

from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from shoplite.extensions import db
from shoplite.utils import clock

PAYMENT_SUCCEEDED = "succeeded"
PAYMENT_DECLINED = "declined"
PAYMENT_ERROR = "error"
PAYMENT_REFUNDED = "refunded"


class Payment(db.Model):
    """One charge attempt for an order."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    amount_paise: Mapped[int]
    status: Mapped[str] = mapped_column(
        String(20), comment="succeeded, declined, error or refunded."
    )
    gateway_ref: Mapped[str | None] = mapped_column(String(64), comment="Gateway's charge ID.")
    error_code: Mapped[str | None] = mapped_column(
        String(20), comment="ShopLite error code when the charge failed, e.g. SL-PAY-402."
    )
    created_at: Mapped[datetime] = mapped_column(default=clock.utcnow)

    def to_dict(self) -> dict:
        """JSON view of the payment."""
        return {
            "id": self.id,
            "amount_paise": self.amount_paise,
            "status": self.status,
            "gateway_ref": self.gateway_ref,
            "error_code": self.error_code,
            "created_at": self.created_at.isoformat(),
        }
