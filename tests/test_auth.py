"""Registration, login and tokens."""

from datetime import timedelta


def test_register_returns_user_without_password(client):
    """A new account is returned without its password hash."""
    response = client.post("/auth/register", json={
        "email": "Asha@Example.test", "name": "Asha", "password": "long-enough-1"})
    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "asha@example.test"
    assert "password_hash" not in body


def test_register_duplicate_email_is_409(client, customer):
    """Emails are unique, ignoring case."""
    customer("dup@shoplite.test")
    response = client.post("/auth/register", json={
        "email": "DUP@shoplite.test", "name": "Again", "password": "long-enough-1"})
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "SL-AUTH-409"


def test_register_rejects_short_password(client):
    """Passwords under 8 characters are rejected."""
    response = client.post("/auth/register", json={
        "email": "a@b.test", "name": "A", "password": "short"})
    assert response.status_code == 422
    assert response.get_json()["error"]["details"]["field"] == "password"


def test_register_rejects_wrong_types(client):
    """A non-string email is a 422 naming the field."""
    response = client.post("/auth/register", json={"email": 42, "name": "A", "password": "x" * 9})
    assert response.status_code == 422
    assert response.get_json()["error"]["details"]["field"] == "email"


def test_register_rejects_non_object_body(client):
    """A JSON list instead of an object is a 422."""
    response = client.post("/auth/register", json=["not", "an", "object"])
    assert response.status_code == 422


def test_login_wrong_password_is_401(client, customer):
    """A wrong password gets the same message as an unknown email."""
    customer("who@shoplite.test")
    wrong = client.post("/auth/login", json={"email": "who@shoplite.test", "password": "nope-nope"})
    unknown = client.post("/auth/login", json={"email": "ghost@shoplite.test", "password": "x" * 9})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json()["error"]["message"] == unknown.get_json()["error"]["message"]


def test_me_requires_token(client):
    """No token means 401."""
    assert client.get("/auth/me").status_code == 401


def test_me_with_bad_scheme_is_401(client):
    """Only 'Bearer' tokens are accepted."""
    assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_me_returns_current_user(client, customer):
    """A valid token identifies the user."""
    headers = customer("me@shoplite.test")
    assert client.get("/auth/me", headers=headers).get_json()["email"] == "me@shoplite.test"


def test_logout_revokes_token(client, customer):
    """After logout the same token is rejected."""
    headers = customer()
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_token_expires(client, customer, move_clock):
    """Tokens stop working after the TTL (24 h by default)."""
    headers = customer()
    move_clock(timedelta(hours=25))
    assert client.get("/auth/me", headers=headers).status_code == 401
