import os
import re

from pdf_utils import make_pdf

from app.core.config import settings
from app.models.models import Document
from app.services.pdf_service import NO_TEXT_ERROR, PROCESSING_FAILED_ERROR

UUID_PDF = re.compile(r"^[0-9a-f]{32}\.pdf$")


def uploaded_files() -> set[str]:
    if not os.path.isdir(settings.UPLOAD_DIR):
        return set()
    return set(os.listdir(settings.UPLOAD_DIR))


def test_upload_accepts_pdf_and_stores_uuid_name(client, auth_headers, upload_pdf, db):
    resp = upload_pdf(auth_headers(), filename="../../evil.pdf")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "evil.pdf"
    assert "original_text" not in body and "file_path" not in body

    doc = db.get(Document, body["id"])
    assert os.path.dirname(os.path.abspath(doc.file_path)) == os.path.abspath(settings.UPLOAD_DIR)
    assert UUID_PDF.match(os.path.basename(doc.file_path))
    assert os.path.exists(doc.file_path)


def test_same_filename_from_two_users_gets_two_files(client, auth_headers, upload_pdf, db):
    upload_pdf(auth_headers("a@example.com"), filename="notes.pdf")
    upload_pdf(auth_headers("b@example.com"), filename="notes.pdf")
    paths = {d.file_path for d in db.query(Document).all()}
    assert len(paths) == 2


def test_upload_rejects_non_pdf_with_415(client, auth_headers):
    headers = auth_headers()
    cases = [
        ("notes.txt", b"%PDF-1.4 but wrong extension", "application/pdf"),
        ("notes.pdf", b"just some text, no magic bytes", "application/pdf"),
        ("notes.pdf", make_pdf(["hello"]), "text/plain"),
    ]
    for name, data, ctype in cases:
        resp = client.post("/api/documents/upload", headers=headers, files={"file": (name, data, ctype)})
        assert resp.status_code == 415, (name, ctype, resp.text)
    assert uploaded_files() == set()


def test_upload_over_limit_is_413_and_leaves_no_file(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    headers = auth_headers()
    before = uploaded_files()
    # 1.5 MiB passes the Content-Length fast path and is caught while streaming;
    # 3 MiB is rejected from the header alone.
    for size in (int(1.5 * 1024 * 1024), 3 * 1024 * 1024):
        data = b"%PDF-1.4\n" + b"0" * size
        resp = client.post("/api/documents/upload", headers=headers, files={"file": ("big.pdf", data, "application/pdf")})
        assert resp.status_code == 413, resp.text
    assert uploaded_files() == before


def test_upload_requires_auth(client, sample_pdf_bytes):
    resp = client.post("/api/documents/upload", files={"file": ("a.pdf", sample_pdf_bytes, "application/pdf")})
    assert resp.status_code == 401


def test_background_processing_marks_ready(client, auth_headers, upload_pdf, fake_embedding_service, db):
    headers = auth_headers()
    resp = upload_pdf(headers)
    assert resp.json()["processing_status"] == "processing"

    doc = db.get(Document, resp.json()["id"])
    assert doc.processing_status == "ready"
    assert doc.embedding_complete is True
    assert doc.processing_error is None
    assert "chlorophyll" in doc.original_text
    assert doc.total_chunks > 0
    stored = fake_embedding_service.collection.get(where={"document_id": doc.id})["ids"]
    assert len(stored) == doc.total_chunks

    listed = client.get("/api/documents/", headers=headers).json()
    assert listed[0]["processing_status"] == "ready"
    assert "original_text" not in listed[0]


def test_blank_pdf_is_marked_failed(client, auth_headers, upload_pdf, db):
    resp = upload_pdf(auth_headers(), data=make_pdf([]))
    doc = db.get(Document, resp.json()["id"])
    assert doc.processing_status == "failed"
    assert doc.processing_error == NO_TEXT_ERROR
    assert doc.embedding_complete is False


def test_embedding_failure_is_marked_failed(client, auth_headers, upload_pdf, fake_embedding_service, monkeypatch, db, caplog):
    def boom(document_id, chunks):
        raise RuntimeError("vector store unavailable at 10.0.0.5:8000")

    monkeypatch.setattr(fake_embedding_service, "add_chunks", boom)
    headers = auth_headers()
    with caplog.at_level("ERROR", logger="app.services.pdf_service"):
        resp = upload_pdf(headers)
    doc = db.get(Document, resp.json()["id"])
    assert doc.processing_status == "failed"
    assert doc.embedding_complete is False
    # The user gets a friendly message; the real exception only goes to the log.
    assert doc.processing_error == PROCESSING_FAILED_ERROR
    listed = client.get("/api/documents/", headers=headers).json()[0]
    assert listed["processing_error"] == PROCESSING_FAILED_ERROR
    assert "10.0.0.5" not in str(listed)
    assert any(r.exc_info and "vector store unavailable" in str(r.exc_info[1]) for r in caplog.records)


def test_reprocess_recovers_a_failed_document(client, auth_headers, upload_pdf, fake_embedding_service, monkeypatch, db):
    headers = auth_headers()
    real_add = fake_embedding_service.add_chunks
    monkeypatch.setattr(fake_embedding_service, "add_chunks", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    doc_id = upload_pdf(headers).json()["id"]
    assert db.get(Document, doc_id).processing_status == "failed"

    monkeypatch.setattr(fake_embedding_service, "add_chunks", real_add)
    resp = client.post(f"/api/documents/{doc_id}/reprocess", headers=headers)
    assert resp.status_code == 200, resp.text
    db.expire_all()
    assert db.get(Document, doc_id).processing_status == "ready"


def test_reprocess_other_users_document_is_404(client, auth_headers, upload_pdf):
    doc_id = upload_pdf(auth_headers("owner@example.com")).json()["id"]
    resp = client.post(f"/api/documents/{doc_id}/reprocess", headers=auth_headers("other@example.com"))
    assert resp.status_code == 404


def test_delete_document_removes_file_and_vectors(client, auth_headers, upload_pdf, fake_embedding_service, db):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    path = db.get(Document, doc_id).file_path

    assert client.delete(f"/api/documents/{doc_id}", headers=headers).status_code == 200
    assert not os.path.exists(path)
    assert not fake_embedding_service.collection.get(where={"document_id": doc_id})["ids"]
    db.expire_all()
    assert db.get(Document, doc_id) is None


def _set_processing(db, doc_id, minutes_ago: int) -> None:
    from sqlalchemy import text

    db.execute(
        text(
            "UPDATE documents SET processing_status = 'processing', "
            "updated_at = now() - make_interval(mins => :m) WHERE id = :id"
        ),
        {"m": minutes_ago, "id": doc_id},
    )
    db.commit()


def test_reprocess_refuses_fresh_processing_but_accepts_stale(client, auth_headers, upload_pdf, db):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]

    _set_processing(db, doc_id, minutes_ago=1)
    assert client.post(f"/api/documents/{doc_id}/reprocess", headers=headers).status_code == 409

    _set_processing(db, doc_id, minutes_ago=11)
    resp = client.post(f"/api/documents/{doc_id}/reprocess", headers=headers)
    assert resp.status_code == 200, resp.text
    db.expire_all()
    assert db.get(Document, doc_id).processing_status == "ready"


def test_document_deleted_during_processing_leaves_no_row_or_vectors(
    client, auth_headers, upload_pdf, fake_embedding_service, monkeypatch, db
):
    from sqlalchemy import text

    from app.models.database import engine

    real_add = fake_embedding_service.add_chunks

    def add_then_user_deletes(document_id, chunks):
        real_add(document_id, chunks)
        # The user deletes the document while the task is still running.
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM documents WHERE id = :id"), {"id": document_id})

    monkeypatch.setattr(fake_embedding_service, "add_chunks", add_then_user_deletes)
    resp = upload_pdf(auth_headers())
    assert resp.status_code == 200
    doc_id = resp.json()["id"]

    assert db.get(Document, doc_id) is None
    assert not fake_embedding_service.collection.get(where={"document_id": doc_id})["ids"]


def test_document_list_is_newest_first(client, auth_headers, upload_pdf):
    headers = auth_headers()
    ids = [upload_pdf(headers, filename=f"doc{i}.pdf").json()["id"] for i in range(3)]
    listed = [d["id"] for d in client.get("/api/documents/", headers=headers).json()]
    assert listed == list(reversed(ids))


def test_rename_and_folder_strip_whitespace(client, auth_headers, upload_pdf):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    resp = client.put(f"/api/documents/{doc_id}/rename", headers=headers, json={"filename": "  Chapter 1.pdf  "})
    assert resp.status_code == 200
    assert resp.json()["filename"] == "Chapter 1.pdf"
    resp = client.put(f"/api/documents/{doc_id}/folder", headers=headers, json={"folder": "  Biology "})
    assert resp.status_code == 200
    assert resp.json()["folder"] == "Biology"


def test_rename_and_folder_validation_is_422_not_500(client, auth_headers, upload_pdf, db):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    for name in ["", "   ", "x" * 256]:
        assert client.put(f"/api/documents/{doc_id}/rename", headers=headers, json={"filename": name}).status_code == 422
    for folder in ["", "   ", "f" * 101]:
        assert client.put(f"/api/documents/{doc_id}/folder", headers=headers, json={"folder": folder}).status_code == 422
    # The limits themselves are accepted.
    assert client.put(f"/api/documents/{doc_id}/rename", headers=headers, json={"filename": "x" * 255}).status_code == 200
    assert client.put(f"/api/documents/{doc_id}/folder", headers=headers, json={"folder": "f" * 100}).status_code == 200
    db.expire_all()
    doc = db.get(Document, doc_id)
    assert (len(doc.filename), len(doc.folder)) == (255, 100)
