"""The fake gateway and the payments endpoint."""

import pytest

from shoplite.payments import gateway


def test_charge_success_is_idempotent():
    """The same idempotency key gives the same charge reference."""
    first = gateway.charge(100, "tok_success", "SL-1")
    assert first.succeeded
    assert gateway.charge(100, "tok_success", "SL-1").gateway_ref == first.gateway_ref


def test_charge_declined_and_unknown_tokens():
    """tok_declined and unknown tokens are declined with SL-PAY-402."""
    for token in ("tok_declined", "tok_anything"):
        result = gateway.charge(100, token, "SL-2")
        assert not result.succeeded
        assert result.error_code == "SL-PAY-402"


def test_charge_gateway_down_raises():
    """tok_gateway_down simulates a timeout."""
    with pytest.raises(gateway.GatewayUnavailable):
        gateway.charge(100, "tok_gateway_down", "SL-3")


def test_charge_rejects_non_positive_amount():
    """Zero or negative charges are a programming error."""
    with pytest.raises(ValueError):
        gateway.charge(0, "tok_success", "SL-4")


def test_payments_listed_for_owner_only(client, customer, product, buy):
    """Owners see their payment attempts; others get a 404."""
    owner, other = customer(), customer()
    order_id = buy(owner, {product(): 1}, payment_token="tok_declined").get_json()["error"][
        "details"]["order_id"]
    payments = client.get(f"/orders/{order_id}/payments", headers=owner).get_json()["items"]
    assert [p["status"] for p in payments] == ["declined"]
    assert client.get(f"/orders/{order_id}/payments", headers=other).status_code == 404
