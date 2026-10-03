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
