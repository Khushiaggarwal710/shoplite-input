"""Product reviews."""


def test_buyer_can_review_once(client, customer, product, buy):
    """A buyer can post one review; a second is a 409."""
    headers, sku = customer(), product()
    buy(headers, {sku: 1})
    review = {"rating": 4, "title": "Solid", "body": "Does the job."}
    assert client.post(f"/products/{sku}/reviews", headers=headers, json=review).status_code == 201
    again = client.post(f"/products/{sku}/reviews", headers=headers, json=review)
    assert again.get_json()["error"]["code"] == "SL-REV-409"


def test_non_buyer_cannot_review(client, customer, product, buy):
    """Customers who haven't bought (or whose payment failed) get a 403."""
    headers, sku = customer(), product()
    buy(headers, {sku: 1}, payment_token="tok_declined")
    response = client.post(f"/products/{sku}/reviews", headers=headers,
                           json={"rating": 5, "title": "Great"})
    assert response.get_json()["error"]["code"] == "SL-REV-403"


def test_rating_must_be_1_to_5(client, customer, product, buy):
    """Ratings outside 1-5 are rejected."""
    headers, sku = customer(), product()
    buy(headers, {sku: 1})
    for rating in (0, 6, "5"):
        response = client.post(f"/products/{sku}/reviews", headers=headers,
                               json={"rating": rating, "title": "x"})
        assert response.status_code == 422, rating


def test_list_reviews_with_average(client, customer, product, buy):
    """The list includes an average rating."""
    sku = product()
    for rating in (5, 2):
        headers = customer()
        buy(headers, {sku: 1})
        client.post(f"/products/{sku}/reviews", headers=headers,
                    json={"rating": rating, "title": "t"})
    body = client.get(f"/products/{sku}/reviews").get_json()
    assert body["total"] == 2
    assert body["rating"] == {"count": 2, "average": 3.5}


def post_review(client, customer, product, buy) -> tuple[str, int]:
    """Have a buyer review a new product; returns (sku, review_id)."""
    headers, sku = customer(), product()
    buy(headers, {sku: 1})
    review = client.post(f"/products/{sku}/reviews", headers=headers,
                         json={"rating": 1, "title": "Buy my course at spam.example"})
    return sku, review.get_json()["id"]


def test_three_flags_hide_a_review(client, customer, product, buy, admin_headers):
    """The third flag hides the review from the product page and rating."""
    sku, review_id = post_review(client, customer, product, buy)
    for _ in range(3):
        response = client.post(f"/reviews/{review_id}/flag", headers=customer(),
                               json={"reason": "spam"})
    assert response.get_json() == {"id": review_id, "status": "hidden", "flags": 3}
    page = client.get(f"/products/{sku}/reviews").get_json()
    assert page["total"] == 0
    assert page["rating"]["count"] == 0
    hidden = client.get("/reviews/hidden", headers=admin_headers).get_json()["items"]
    assert [r["id"] for r in hidden] == [review_id]


def test_flag_rules(client, customer, product, buy):
    """One flag per user, a known reason, and not your own review."""
    headers, sku = customer(), product()
    buy(headers, {sku: 1})
    review_id = client.post(f"/products/{sku}/reviews", headers=headers,
                            json={"rating": 4, "title": "Fine"}).get_json()["id"]
    own = client.post(f"/reviews/{review_id}/flag", headers=headers, json={"reason": "spam"})
    assert own.status_code == 403
    other = customer()
    bad_reason = client.post(f"/reviews/{review_id}/flag", headers=other, json={"reason": "meh"})
    assert bad_reason.status_code == 422
    client.post(f"/reviews/{review_id}/flag", headers=other, json={"reason": "spam"})
    again = client.post(f"/reviews/{review_id}/flag", headers=other, json={"reason": "spam"})
    assert again.status_code == 409


def test_flag_unknown_review_is_404(client, customer):
    """Flagging a missing review is a 404."""
    response = client.post("/reviews/999/flag", headers=customer(), json={"reason": "spam"})
    assert response.status_code == 404


def test_hidden_list_is_admin_only(client, customer):
    """Customers can't see hidden reviews."""
    assert client.get("/reviews/hidden", headers=customer()).status_code == 403
