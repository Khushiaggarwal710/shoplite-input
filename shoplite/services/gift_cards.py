"""Issuing and spending gift cards."""

import secrets
from datetime import datetime

from sqlalchemy import select

from shoplite.errors import NotFound, ValidationError
from shoplite.extensions import db
from shoplite.models import GiftCard
from shoplite.utils import clock

MAX_GIFT_CARD_PAISE = 1_000_000  # ₹10,000


def issue_gift_card(amount_paise: int, expires_at: datetime | None = None) -> GiftCard:
    """Create a card worth up to ₹10,000."""
    if not 0 < amount_paise <= MAX_GIFT_CARD_PAISE:
        raise ValidationError("gift cards must be worth between ₹0.01 and ₹10,000",
                              details={"field": "amount"})
    card = GiftCard(code=f"GC-{secrets.token_hex(4).upper()}", initial_paise=amount_paise,
                    balance_paise=amount_paise, expires_at=expires_at)
    db.session.add(card)
    db.session.commit()
    return card


def get_gift_card(code: str) -> GiftCard:
    """Find a card by code or raise NotFound."""
    card = db.session.scalar(select(GiftCard).where(GiftCard.code == code.upper()))
    if card is None:
        raise NotFound(f"no gift card {code.upper()}", code="SL-GFT-404")
    return card


def usable_card(code: str) -> GiftCard:
    """Return the card if it is active, unexpired and has a balance."""
    card = get_gift_card(code)
    if not card.is_active or card.balance_paise == 0:
        raise ValidationError(f"{card.code} has no balance left", code="SL-GFT-422")
    if card.expires_at is not None and card.expires_at <= clock.utcnow():
        raise ValidationError(f"{card.code} has expired", code="SL-GFT-422")
    return card


def amount_covered(card: GiftCard, total_paise: int) -> int:
    """How much of the total the card can pay."""
    return min(card.balance_paise, total_paise)
