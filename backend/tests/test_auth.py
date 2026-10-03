import pytest
from conftest import TEST_PASSWORD

from app.models.models import Document, User


def register(client, email="a@example.com", password=TEST_PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password, "name": "A"})


def test_register_returns_token_and_user(client):
    resp = register(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == "a@example.com"


def test_register_duplicate_email_is_400(client):
    assert register(client).status_code == 200
    assert register(client).status_code == 400


def test_register_rejects_short_and_overlong_passwords(client):
    assert register(client, password="short").status_code == 400
    assert register(client, password="x" * 73).status_code == 400


def test_login_success(client):
    register(client)
    resp = client.post("/api/auth/login", json={"email": "a@example.com", "password": TEST_PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_wrong_password_is_401(client):
    register(client)
    resp = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_unknown_email_is_401(client):
    resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD})
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_me_with_token(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers("me@example.com"))
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_delete_account_removes_files_vectors_and_rows(client, auth_headers, upload_pdf, fake_embedding_service, db):
    headers = auth_headers("leaver@example.com")
    doc_id = upload_pdf(headers).json()["id"]
    doc = db.get(Document, doc_id)
    file_path = doc.file_path
    assert fake_embedding_service.collection.get(where={"document_id": doc_id})["ids"]

    resp = client.request("DELETE", "/api/auth/me", headers=headers, json={"password": TEST_PASSWORD})
    assert resp.status_code == 200

    db.expire_all()
    assert db.query(User).count() == 0
    assert db.query(Document).count() == 0
    assert not fake_embedding_service.collection.get(where={"document_id": doc_id})["ids"]
    import os
    assert not os.path.exists(file_path)


# --- Email validation and normalisation -----------------------------------

def test_register_rejects_invalid_email(client):
    for bad in ["not-an-email", "a@", "@example.com", "a b@example.com", ""]:
        assert register(client, email=bad).status_code == 422, bad


def test_register_lowercases_email_and_blocks_case_duplicates(client, db):
    resp = register(client, email="  Mixed.Case@Example.COM ")
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["email"] == "mixed.case@example.com"
    assert db.query(User).one().email == "mixed.case@example.com"

    assert register(client, email="MIXED.case@example.com").status_code == 400


def test_login_is_case_insensitive(client):
    register(client, email="casey@example.com")
    resp = client.post("/api/auth/login", json={"email": "CASEY@Example.com", "password": TEST_PASSWORD})
    assert resp.status_code == 200


def test_login_finds_legacy_mixed_case_account(client, db):
    from app.api.routes.auth import hash_password
    db.add(User(email="Legacy@Example.com", hashed_password=hash_password(TEST_PASSWORD), name="L"))
    db.commit()
    resp = client.post("/api/auth/login", json={"email": "legacy@example.com", "password": TEST_PASSWORD})
    assert resp.status_code == 200
    assert register(client, email="legacy@example.com").status_code == 400


def test_login_errors_do_not_reveal_registered_emails(client, db):
    register(client)
    db.add(User(email="google-only@example.com", name="G"))
    db.commit()
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": TEST_PASSWORD})
    wrong = client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    google = client.post("/api/auth/login", json={"email": "google-only@example.com", "password": TEST_PASSWORD})
    assert unknown.status_code == wrong.status_code == google.status_code == 401
    assert unknown.json() == wrong.json() == google.json() == {"detail": "Invalid email or password"}


def test_google_login_normalises_email_and_reuses_account(client, monkeypatch):
    from app.api.routes import auth as auth_routes

    register(client, email="pat@example.com")
    monkeypatch.setattr(
        auth_routes.id_token,
        "verify_oauth2_token",
        lambda *a, **k: {"aud": "test-client-placeholder", "email": "Pat@Example.com", "name": "Pat"},
    )
    resp = client.post("/api/auth/google", json={"credential": "fake"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["email"] == "pat@example.com"
    assert resp.json()["user"]["has_password"] is True


# --- Tokens for deleted users ---------------------------------------------

def test_token_of_deleted_user_is_401_everywhere(client, auth_headers, db):
    headers = auth_headers("ghost@example.com")
    db.query(User).delete()
    db.commit()
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.get("/api/auth/me/stats", headers=headers).status_code == 401
    assert client.get("/api/documents/", headers=headers).status_code == 401
    assert client.get("/api/quizzes/", headers=headers).status_code == 401
    assert client.post("/api/chat/", headers=headers, json={"question": "hi"}).status_code == 401


def test_delete_account_wrong_password_is_403_not_401(client, auth_headers):
    headers = auth_headers()
    resp = client.request("DELETE", "/api/auth/me", headers=headers, json={"password": "wrong-password"})
    assert resp.status_code == 403


# --- Profile name and password changes -------------------------------------

def test_update_name(client, auth_headers):
    headers = auth_headers()
    resp = client.put("/api/auth/me", headers=headers, json={"name": "  New Name  "})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert client.get("/api/auth/me", headers=headers).json()["name"] == "New Name"


def test_update_name_validation_is_422(client, auth_headers):
    headers = auth_headers()
    assert client.put("/api/auth/me", headers=headers, json={"name": "   "}).status_code == 422
    assert client.put("/api/auth/me", headers=headers, json={"name": "x" * 256}).status_code == 422
    assert client.put("/api/auth/me", json={"name": "Anon"}).status_code == 401


def _login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_change_password(client, auth_headers):
    headers = auth_headers("pw@example.com")
    resp = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": "Brand-new-password"},
    )
    assert resp.status_code == 200, resp.text
    assert _login(client, "pw@example.com", TEST_PASSWORD).status_code == 401
    assert _login(client, "pw@example.com", "Brand-new-password").status_code == 200


def test_change_password_requires_correct_current_password(client, auth_headers):
    headers = auth_headers("pw@example.com")
    wrong = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"current_password": "not-it-at-all", "new_password": "Brand-new-password"},
    )
    missing = client.put("/api/auth/me/password", headers=headers, json={"new_password": "Brand-new-password"})
    assert wrong.status_code == missing.status_code == 403
    assert _login(client, "pw@example.com", TEST_PASSWORD).status_code == 200


def test_change_password_enforces_length_rules(client, auth_headers):
    headers = auth_headers()
    for bad in ["short", "x" * 73]:
        resp = client.put(
            "/api/auth/me/password",
            headers=headers,
            json={"current_password": TEST_PASSWORD, "new_password": bad},
        )
        assert resp.status_code == 400


@pytest.fixture
def google_only(client, db):
    from app.api.routes.auth import create_access_token

    user = User(email="g@example.com", name="G")
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {create_access_token({'sub': user.email, 'user_id': user.id})}"}


@pytest.fixture
def google_token(monkeypatch):
    """Stub Google verification: credential 'good:<email>' verifies as <email>."""
    from app.api.routes import auth as auth_routes

    calls = []

    def verify(credential, request, audience):
        calls.append(credential)
        if not credential.startswith("good:"):
            raise ValueError("Token used too late")
        return {"aud": audience, "email": credential[len("good:"):], "name": "G"}

    monkeypatch.setattr(auth_routes.id_token, "verify_oauth2_token", verify)
    return calls


def test_google_only_user_needs_google_credential_to_set_password(client, google_only, google_token):
    assert client.get("/api/auth/me", headers=google_only).json()["has_password"] is False
    resp = client.put("/api/auth/me/password", headers=google_only, json={"new_password": "First-password"})
    assert resp.status_code == 403
    resp = client.put(
        "/api/auth/me/password",
        headers=google_only,
        json={"new_password": "First-password", "google_credential": "expired-or-forged"},
    )
    assert resp.status_code == 403
    assert _login(client, "g@example.com", "First-password").status_code == 401


def test_google_credential_for_another_email_is_403(client, google_only, google_token):
    resp = client.put(
        "/api/auth/me/password",
        headers=google_only,
        json={"new_password": "First-password", "google_credential": "good:attacker@example.com"},
    )
    assert resp.status_code == 403
    assert client.get("/api/auth/me", headers=google_only).json()["has_password"] is False


def test_google_only_user_sets_password_with_fresh_google_credential(client, google_only, google_token):
    resp = client.put(
        "/api/auth/me/password",
        headers=google_only,
        json={"new_password": "First-password", "google_credential": "good:G@Example.com"},
    )
    assert resp.status_code == 200, resp.text
    assert google_token == ["good:G@Example.com"]
    assert _login(client, "g@example.com", "First-password").status_code == 200
    assert client.get("/api/auth/me", headers=google_only).json()["has_password"] is True


def test_password_users_do_not_need_google(client, auth_headers, google_token):
    headers = auth_headers("pw@example.com")
    resp = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": "Brand-new-password"},
    )
    assert resp.status_code == 200
    # A Google credential can't stand in for the current password.
    resp = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"new_password": "Another-password", "google_credential": "good:pw@example.com"},
    )
    assert resp.status_code == 403
    assert google_token == []
    assert _login(client, "pw@example.com", "Brand-new-password").status_code == 200


# --- Stats ------------------------------------------------------------------

def test_active_chats_counts_only_documents_with_messages(client, auth_headers, upload_pdf):
    headers = auth_headers()
    first = upload_pdf(headers).json()["id"]
    upload_pdf(headers, filename="second.pdf")
    stats = client.get("/api/auth/me/stats", headers=headers).json()
    assert stats["total_documents"] == 2
    assert stats["active_chats"] == 0

    client.post("/api/chat/", headers=headers, json={"question": "What is this?", "document_id": first})
    assert client.get("/api/auth/me/stats", headers=headers).json()["active_chats"] == 1


# --- Round 2: signup name, password strength, analyzed count ------------------

def test_register_requires_a_real_name(client, db):
    for name in ["", "   ", "x" * 256]:
        resp = client.post("/api/auth/register", json={"email": "n@example.com", "password": TEST_PASSWORD, "name": name})
        assert resp.status_code == 422, name
    resp = client.post("/api/auth/register", json={"email": "n@example.com", "password": TEST_PASSWORD})
    assert resp.status_code == 422
    resp = client.post("/api/auth/register", json={"email": "n@example.com", "password": TEST_PASSWORD, "name": "  Nia  "})
    assert resp.status_code == 200
    assert resp.json()["user"]["name"] == "Nia"


WEAK_PASSWORDS = {
    "no-uppercase-here": "uppercase",
    "NoSymbolsHere123": "symbol",
    "Sh-rt": "at least 8",
}


def test_register_enforces_signup_password_rules(client):
    for password, reason in WEAK_PASSWORDS.items():
        resp = register(client, password=password)
        assert resp.status_code == 400, password
        assert reason in resp.json()["detail"]
    # Any non-alphanumeric character counts as a symbol, like the signup form.
    for i, password in enumerate(["Under_score1", "Dash-dash1", "Space bar1"]):
        assert register(client, email=f"ok{i}@example.com", password=password).status_code == 200


def test_change_password_enforces_signup_password_rules(client, auth_headers):
    headers = auth_headers("rules@example.com")
    for password, reason in WEAK_PASSWORDS.items():
        resp = client.put(
            "/api/auth/me/password",
            headers=headers,
            json={"current_password": TEST_PASSWORD, "new_password": password},
        )
        assert resp.status_code == 400, password
        assert reason in resp.json()["detail"]
    assert _login(client, "rules@example.com", TEST_PASSWORD).status_code == 200


def test_google_only_first_password_enforces_signup_rules(client, google_only, google_token):
    resp = client.put(
        "/api/auth/me/password",
        headers=google_only,
        json={"new_password": "lowercase-only", "google_credential": "good:g@example.com"},
    )
    assert resp.status_code == 400
    assert client.get("/api/auth/me", headers=google_only).json()["has_password"] is False


def test_documents_analyzed_counts_only_ready_documents(client, auth_headers, upload_pdf, db):
    headers = auth_headers()
    ids = [upload_pdf(headers, filename=f"d{i}.pdf").json()["id"] for i in range(3)]
    db.get(Document, ids[0]).processing_status = "failed"
    db.get(Document, ids[1]).processing_status = "processing"
    db.commit()
    assert client.get("/api/auth/me/stats", headers=headers).json()["total_documents"] == 1
