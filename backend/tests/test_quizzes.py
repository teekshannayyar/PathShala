import json

import pytest
from conftest import make_quiz_json

from app.models.models import Document, Question, Quiz


@pytest.fixture
def ready_doc(client, auth_headers, upload_pdf):
    headers = auth_headers()
    doc_id = upload_pdf(headers).json()["id"]
    return headers, doc_id


def test_generate_saves_ten_questions(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    fake_groq.queue(make_quiz_json(10))

    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    quiz_id = resp.json()["quiz_id"]
    assert resp.json()["title"] == "notes"

    quiz = client.get(f"/api/quizzes/{quiz_id}", headers=headers).json()
    assert len(quiz["questions"]) == 10
    assert "correct_answer" not in quiz["questions"][0]
    assert db.query(Question).count() == 10

    call = fake_groq.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert "chlorophyll" in call["messages"][-1]["content"]


def test_invalid_then_valid_reply_succeeds_after_retry(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    fake_groq.queue("this is not json", make_quiz_json(10))

    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(fake_groq.calls) == 2
    retry_messages = fake_groq.calls[1]["messages"]
    assert "Your previous output was invalid" in retry_messages[-1]["content"]
    assert all(c["response_format"] == {"type": "json_object"} for c in fake_groq.calls)
    assert db.query(Question).count() == 10


def test_invalid_twice_is_502_and_saves_nothing(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    fake_groq.queue(json.dumps({"questions": []}), "still not json")

    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Quiz generation failed, please try again"
    assert len(fake_groq.calls) == 2
    assert db.query(Quiz).count() == 0


def test_generate_while_processing_is_409(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    db.get(Document, doc_id).processing_status = "processing"
    db.commit()

    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers)
    assert resp.status_code == 409
    assert fake_groq.calls == []


def test_generate_on_failed_document_is_422(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    db.get(Document, doc_id).processing_status = "failed"
    db.commit()

    assert client.post(f"/api/quizzes/generate/{doc_id}", headers=headers).status_code == 422
    assert fake_groq.calls == []


def test_generate_for_another_users_document_is_404(client, ready_doc, auth_headers, fake_groq):
    _, doc_id = ready_doc
    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=auth_headers("other@example.com"))
    assert resp.status_code == 404


def test_submit_scores_answers(client, ready_doc, fake_llm):
    headers, doc_id = ready_doc
    quiz_id = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers).json()["quiz_id"]
    questions = client.get(f"/api/quizzes/{quiz_id}", headers=headers).json()["questions"]

    answers = [{"question_id": q["id"], "user_answer": q["options"][1]} for q in questions[:6]]
    answers += [{"question_id": q["id"], "user_answer": q["options"][0]} for q in questions[6:]]
    resp = client.post(f"/api/quizzes/{quiz_id}/submit", headers=headers, json={"answers": answers})
    assert resp.status_code == 200
    assert resp.json()["score"] == 6
    assert resp.json()["total"] == 10


def _groq_bad_request(code: str):
    import groq
    import httpx

    request = httpx.Request("POST", "https://api.groq.invalid/openai/v1/chat/completions")
    body = {"error": {"message": "rejected", "type": "invalid_request_error", "code": code}}
    return groq.BadRequestError("rejected", response=httpx.Response(400, request=request, json=body), body=body)


def test_groq_json_validate_failed_is_retried(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    fake_groq.queue(_groq_bad_request("json_validate_failed"), make_quiz_json(10))

    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(fake_groq.calls) == 2
    assert db.query(Question).count() == 10


def test_other_groq_bad_request_is_not_retried(client, ready_doc, fake_groq, db):
    headers, doc_id = ready_doc
    fake_groq.queue(_groq_bad_request("model_not_found"), make_quiz_json(10))

    resp = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers)
    assert resp.status_code == 502
    assert len(fake_groq.calls) == 1
    assert db.query(Quiz).count() == 0
