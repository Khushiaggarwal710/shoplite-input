"""Gift cards."""


def issue(client, admin_headers, amount: str, **extra) -> str:
    """Issue a gift card and return its code."""
    response = client.post("/gift-cards", headers=admin_headers, json={"amount": amount, **extra})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["code"]


def place(client, headers, sku, **extra):
    """Add one unit and check out."""
    client.post("/cart/items", headers=headers, json={"sku": sku, "quantity": 1})
    return client.post("/orders", headers=headers, json={
        "payment_token": "tok_success", "shipping_pincode": "560001", **extra})


def test_gift_card_pays_part_of_the_order(client, admin_headers, customer, product):
    """The card covers what it can; the rest goes to the payment card."""
    headers, code = customer(), issue(client, admin_headers, "200.00")
    order = place(client, headers, product(price="500.00"), gift_card_code=code).get_json()
    assert order["gift_card_paise"] == 20000
    payments = client.get(f"/orders/{order['id']}/payments", headers=headers).get_json()
    assert payments["items"][0]["amount_paise"] == 50000 + 4900 - 20000
    assert client.get(f"/gift-cards/{code}", headers=headers).get_json()["balance_paise"] == 0


def test_gift_card_covers_whole_order_without_charging(client, admin_headers, customer, product):
    """When the card covers everything, the gateway is not called."""
    headers, code = customer(), issue(client, admin_headers, "5000.00")
    order = place(client, headers, product(price="100.00"), gift_card_code=code,
                  payment_token="tok_gateway_down").get_json()
    assert order["status"] == "paid"
    balance = client.get(f"/gift-cards/{code}", headers=headers).get_json()["balance_paise"]
    assert balance == 500000 - (10000 + 4900)


def test_declined_payment_keeps_gift_card_balance(client, admin_headers, customer, product):
    """If the card part is declined, the gift card isn't charged."""
    headers, code = customer(), issue(client, admin_headers, "100.00")
    response = place(client, headers, product(price="500.00"), gift_card_code=code,
                     payment_token="tok_declined")
    assert response.status_code == 402
    assert client.get(f"/gift-cards/{code}", headers=headers).get_json()["balance_paise"] == 10000


def test_refund_returns_gift_card_balance(client, admin_headers, customer, product):
    """A refund puts the gift-card part back on the card."""
    headers, code = customer(), issue(client, admin_headers, "300.00")
    order_id = place(client, headers, product(price="500.00"), gift_card_code=code).get_json()["id"]
    client.post(f"/orders/{order_id}/refund", headers=admin_headers)
    assert client.get(f"/gift-cards/{code}", headers=headers).get_json()["balance_paise"] == 30000


def test_unknown_empty_or_expired_cards(client, admin_headers, customer, product):
    """Unknown codes are 404; used-up and expired cards are 422."""
    headers, sku = customer(), product(price="50.00")
    assert place(client, headers, sku, gift_card_code="GC-NOPE").status_code == 404
    expired = issue(client, admin_headers, "10.00", expires_at="2020-01-01T00:00:00")
    assert place(client, headers, sku, gift_card_code=expired).status_code == 422
    small = issue(client, admin_headers, "10.00")
    place(client, headers, sku, gift_card_code=small)
    response = place(client, headers, sku, gift_card_code=small)
    assert response.get_json()["error"]["code"] == "SL-GFT-422"


def test_issuing_is_admin_only_and_validated(client, admin_headers, customer):
    """Customers can't issue cards; amounts must be positive and at most ₹10,000."""
    assert client.post("/gift-cards", headers=customer(), json={"amount": "10"}).status_code == 403
    for amount in ("0", "10000.01", "abc"):
        response = client.post("/gift-cards", headers=admin_headers, json={"amount": amount})
        assert response.status_code == 422, amount
