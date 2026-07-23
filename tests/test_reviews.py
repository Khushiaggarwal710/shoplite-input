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
