"""Rate limits are off in the rest of the suite; these tests switch them on."""
import pytest

from app.core.rate_limit import limiter

ORIGIN = "http://localhost:5173"  # the FRONTEND_URL conftest sets


@pytest.fixture
def rate_limits_on(client, monkeypatch):
    monkeypatch.setattr(limiter, "enabled", True)
    limiter.reset()
    yield
    limiter.reset()


def _login(client):
    return client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": "nobody@example.com", "password": "wrong-password"},
    )


def test_eleventh_login_in_a_minute_is_429(client, rate_limits_on):
    codes = [_login(client).status_code for _ in range(10)]
    assert codes == [401] * 10

    resp = _login(client)
    assert resp.status_code == 429
    # The frontend reads FastAPI's "detail", and the browser needs CORS
    # headers on the 429 to let the app see it at all.
    assert "Too many requests" in resp.json()["detail"]
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_each_auth_endpoint_has_its_own_counter(client, rate_limits_on):
    for i in range(10):
        resp = client.post("/api/auth/register", json={"email": f"u{i}@example.com", "password": "short"})
        assert resp.status_code == 400
    assert client.post("/api/auth/register", json={"email": "u@example.com", "password": "short"}).status_code == 429

    # A different endpoint has its own counter.
    assert _login(client).status_code == 401


def test_chat_is_limited_to_30_per_minute(client, auth_headers, fake_llm, rate_limits_on):
    headers = auth_headers()
    for _ in range(30):
        assert client.post("/api/chat/", headers=headers, json={"question": "hi"}).status_code == 200
    assert client.post("/api/chat/", headers=headers, json={"question": "hi"}).status_code == 429
    assert len(fake_llm.calls) == 30


def test_password_change_is_limited(client, auth_headers, rate_limits_on):
    headers = auth_headers()
    body = {"current_password": "wrong-password", "new_password": "another-password"}
    for _ in range(10):
        assert client.put("/api/auth/me/password", headers=headers, json=body).status_code == 403
    assert client.put("/api/auth/me/password", headers=headers, json=body).status_code == 429


def test_limits_are_off_when_disabled(client):
    assert limiter.enabled is False
    assert all(_login(client).status_code == 401 for _ in range(12))
