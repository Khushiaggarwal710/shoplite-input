"""Gift cards: admins issue them; customers check a balance."""

from datetime import datetime

from flask import Blueprint

from shoplite.api.helpers import json_body, login_required, require_admin
from shoplite.errors import ValidationError
from shoplite.services import gift_cards
from shoplite.utils.money import to_paise
from shoplite.utils.validation import get_str

gift_cards_bp = Blueprint("gift_cards", __name__, url_prefix="/gift-cards")


@gift_cards_bp.post("")
def issue():
    require_admin()
    body = json_body()
    try:
        amount = to_paise(get_str(body, "amount", max_len=20))
        expires_raw = get_str(body, "expires_at", required=False, max_len=40)
        expires_at = datetime.fromisoformat(expires_raw) if expires_raw else None
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
    return gift_cards.issue_gift_card(amount, expires_at).to_dict(), 201


@gift_cards_bp.get("/<code>")
@login_required
def balance(code: str):
    return gift_cards.get_gift_card(code).to_dict()
