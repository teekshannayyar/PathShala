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
        json={"current_password": TEST_PASSWORD, "new_password": "brand-new-password"},
    )
    assert resp.status_code == 200, resp.text
    assert _login(client, "pw@example.com", TEST_PASSWORD).status_code == 401
    assert _login(client, "pw@example.com", "brand-new-password").status_code == 200


def test_change_password_requires_correct_current_password(client, auth_headers):
    headers = auth_headers("pw@example.com")
    wrong = client.put(
        "/api/auth/me/password",
        headers=headers,
        json={"current_password": "not-it-at-all", "new_password": "brand-new-password"},
    )
    missing = client.put("/api/auth/me/password", headers=headers, json={"new_password": "brand-new-password"})
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


def test_google_only_user_can_set_password_without_current(client, db):
    from app.api.routes.auth import create_access_token

    user = User(email="g@example.com", name="G")
    db.add(user)
    db.commit()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': user.email, 'user_id': user.id})}"}
    assert client.get("/api/auth/me", headers=headers).json()["has_password"] is False

    resp = client.put("/api/auth/me/password", headers=headers, json={"new_password": "first-password"})
    assert resp.status_code == 200, resp.text
    assert _login(client, "g@example.com", "first-password").status_code == 200
    assert client.get("/api/auth/me", headers=headers).json()["has_password"] is True


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
