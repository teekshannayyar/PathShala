from app.models.models import ActivityLog, Message


def test_chat_with_another_users_document_is_404(client, auth_headers, upload_pdf, fake_llm, db):
    doc_id = upload_pdf(auth_headers("a@example.com")).json()["id"]
    other = auth_headers("b@example.com")

    assert client.get(f"/api/chat/history/{doc_id}", headers=other).status_code == 404
    resp = client.post("/api/chat/", headers=other, json={"question": "hi", "document_id": doc_id})
    assert resp.status_code == 404

    assert db.query(Message).count() == 0
    # Only the owner's upload logged activity; nothing was written for B.
    assert db.query(ActivityLog).count() == 1
    assert fake_llm.calls == []


def test_history_requires_auth(client, auth_headers, upload_pdf):
    doc_id = upload_pdf(auth_headers()).json()["id"]
    assert client.get(f"/api/chat/history/{doc_id}").status_code == 401
    assert client.post("/api/chat/", json={"question": "hi", "document_id": doc_id}).status_code == 401


def test_chat_saves_messages_and_uses_document_context(client, auth_headers, upload_pdf, fake_llm):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    fake_llm.answers.append("Chlorophyll is a green pigment.")

    resp = client.post("/api/chat/", headers=headers, json={"question": "What does chlorophyll absorb?", "document_id": doc_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["answer"] == "Chlorophyll is a green pigment."
    assert resp.json()["sources"]

    name, kwargs = fake_llm.calls[-1]
    assert name == "generate_response"
    assert any("chlorophyll" in chunk["text"].lower() for chunk in kwargs["context_chunks"])

    history = client.get(f"/api/chat/history/{doc_id}", headers=headers).json()
    assert [(m["role"], m["content"]) for m in history] == [
        ("user", "What does chlorophyll absorb?"),
        ("assistant", "Chlorophyll is a green pigment."),
    ]

    # The next turn sends the earlier exchange as history.
    client.post("/api/chat/", headers=headers, json={"question": "And green light?", "document_id": doc_id})
    _, kwargs = fake_llm.calls[-1]
    assert [m["role"] for m in kwargs["history"]] == ["user", "assistant"]


def test_chat_through_real_llm_service(client, auth_headers, upload_pdf, fake_groq):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    fake_groq.queue("Plants make glucose.")

    resp = client.post("/api/chat/", headers=headers, json={"question": "What is made?", "document_id": doc_id})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "Plants make glucose."
    call = fake_groq.calls[0]
    assert call["model"] == "test-model"
    assert "Photosynthesis" in call["messages"][-1]["content"]


def test_llm_failure_is_a_clean_502(client, auth_headers, upload_pdf, fake_groq):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    fake_groq.queue(ConnectionError("groq unreachable"))

    resp = client.post("/api/chat/", headers=headers, json={"question": "Hi?", "document_id": doc_id})
    assert resp.status_code == 502
    assert "groq" not in resp.text.lower()


def test_chat_question_must_be_1_to_4000_chars(client, auth_headers, upload_pdf, fake_llm, db):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    for question in ["", "   \n ", "x" * 4001]:
        resp = client.post("/api/chat/", headers=headers, json={"question": question, "document_id": doc_id})
        assert resp.status_code == 422
    assert fake_llm.calls == []
    assert db.query(Message).count() == 0

    resp = client.post("/api/chat/", headers=headers, json={"question": "  " + "x" * 4000 + "  ", "document_id": doc_id})
    assert resp.status_code == 200
    assert fake_llm.calls[0][1]["prompt"] == "x" * 4000
