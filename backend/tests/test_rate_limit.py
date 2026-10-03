"""Rate limits are off in the rest of the suite; these tests switch them on."""
import pytest

from app.core.config import settings
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
        # Rejected by the handler's strength check (no capital), but still counted.
        resp = client.post("/api/auth/register", json={"name": "Student", "email": f"u{i}@example.com", "password": "longenough-1"})
        assert resp.status_code == 400
    assert client.post("/api/auth/register", json={"name": "Student", "email": "u@example.com", "password": "longenough-1"}).status_code == 429

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


def test_spoofed_x_forwarded_for_does_not_reset_the_counter(client, rate_limits_on):
    for i in range(10):
        resp = client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": f"198.51.100.{i}"},
            json={"email": "nobody@example.com", "password": "wrong-password"},
        )
        assert resp.status_code == 401
    resp = client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "198.51.100.99"},
        json={"email": "nobody@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 429


def test_client_ip_header_is_the_key_when_configured(client, rate_limits_on, monkeypatch):
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "cf-connecting-ip")

    def login_as(ip):
        return client.post(
            "/api/auth/login",
            headers={"CF-Connecting-IP": ip},
            json={"email": "nobody@example.com", "password": "wrong-password"},
        )

    assert [login_as("203.0.113.1").status_code for _ in range(10)] == [401] * 10
    assert login_as("203.0.113.1").status_code == 429
    # A different client behind the same proxy has its own counter, and the
    # first value of a comma-separated header is used.
    assert login_as(" 203.0.113.2 , 10.0.0.1").status_code == 401


def test_client_ip_falls_back_to_the_peer_address():
    from starlette.requests import Request

    from app.core.rate_limit import client_ip

    def request(headers):
        return Request({"type": "http", "headers": headers, "client": ("192.0.2.7", 1234)})

    assert client_ip(request([])) == "192.0.2.7"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "CLIENT_IP_HEADER", "cf-connecting-ip")
        assert client_ip(request([])) == "192.0.2.7"
        assert client_ip(request([(b"cf-connecting-ip", b"  ")])) == "192.0.2.7"
        assert client_ip(request([(b"cf-connecting-ip", b"203.0.113.5")])) == "203.0.113.5"
