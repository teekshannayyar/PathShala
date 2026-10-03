"""Study days are the user's local calendar days (X-Timezone), with a fixed clock."""
import datetime

import pytest

from app.api.routes.auth import compute_streaks
from app.core import timezone as tz_module
from app.core.timezone import UTC, local_today, parse_timezone
from app.models.models import ActivityLog, Document, Message

# 20:00 UTC on Oct 3 is already 01:30 on Oct 4 in India (UTC+5:30).
FIXED_NOW = datetime.datetime(2026, 10, 3, 20, 0, tzinfo=datetime.timezone.utc)
KOLKATA = {"X-Timezone": "Asia/Kolkata"}


def utc(*args) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=datetime.timezone.utc)


@pytest.fixture
def fixed_now(monkeypatch):
    monkeypatch.setattr(tz_module, "now_utc", lambda: FIXED_NOW)
    return FIXED_NOW


@pytest.mark.parametrize(
    "value", [None, "", "   ", "Not/AZone", "../../etc/passwd", "/etc/localtime", "UTC+5", "A" * 200]
)
def test_invalid_or_missing_timezone_falls_back_to_utc(value):
    assert parse_timezone(value) is UTC


def test_valid_timezone_is_used():
    assert parse_timezone(" Asia/Kolkata ").key == "Asia/Kolkata"


def test_local_today_uses_the_users_calendar_day(fixed_now):
    assert local_today(parse_timezone("Asia/Kolkata")) == "2026-10-04"
    assert local_today(parse_timezone("America/Los_Angeles")) == "2026-10-03"
    assert local_today(UTC) == "2026-10-03"


def test_chat_logs_activity_on_the_local_date(client, auth_headers, fake_llm, fixed_now, db):
    headers = auth_headers()
    resp = client.post("/api/chat/", headers={**headers, **KOLKATA}, json={"question": "hi"})
    assert resp.status_code == 200, resp.text
    assert [log.date_string for log in db.query(ActivityLog).all()] == ["2026-10-04"]


def test_invalid_timezone_header_logs_utc_date(client, auth_headers, fake_llm, fixed_now, db):
    headers = auth_headers()
    resp = client.post("/api/chat/", headers={**headers, "X-Timezone": "Mars/Olympus_Mons"}, json={"question": "hi"})
    assert resp.status_code == 200, resp.text
    assert [log.date_string for log in db.query(ActivityLog).all()] == ["2026-10-03"]


def test_upload_and_quiz_submit_log_one_row_per_local_day(client, auth_headers, upload_pdf, fake_llm, fixed_now, db):
    headers = {**auth_headers(), **KOLKATA}
    doc_id = upload_pdf(headers).json()["id"]
    quiz_id = client.post(f"/api/quizzes/generate/{doc_id}", headers=headers).json()["quiz_id"]
    assert client.post(f"/api/quizzes/{quiz_id}/submit", headers=headers, json={"answers": []}).status_code == 200

    # Same local day twice: still one row.
    assert [log.date_string for log in db.query(ActivityLog).all()] == ["2026-10-04"]


def _user_id(client, headers) -> int:
    return client.get("/api/auth/me", headers=headers).json()["id"]


def test_stats_bucket_timestamps_by_local_day(client, auth_headers, fixed_now, db):
    headers = auth_headers()
    user_id = _user_id(client, headers)
    # Kolkata days: Oct 2 (00:30), Oct 2, Oct 4 (00:30). UTC days: Oct 1, 2, 3.
    doc_a = Document(filename="a.pdf", owner_id=user_id, created_at=utc(2026, 10, 1, 19, 0))
    doc_b = Document(filename="b.pdf", owner_id=user_id, created_at=utc(2026, 10, 2, 12, 0))
    db.add_all([doc_a, doc_b])
    db.flush()
    db.add(Message(document_id=doc_b.id, role="user", content="hi", created_at=utc(2026, 10, 3, 19, 0)))
    db.commit()

    local = client.get("/api/auth/me/stats", headers={**headers, **KOLKATA}).json()
    assert local["activity_dates"] == ["2026-10-02", "2026-10-04"]
    assert (local["current_streak"], local["highest_streak"]) == (1, 1)

    in_utc = client.get("/api/auth/me/stats", headers=headers).json()
    assert in_utc["activity_dates"] == ["2026-10-01", "2026-10-02", "2026-10-03"]
    assert (in_utc["current_streak"], in_utc["highest_streak"]) == (3, 3)


def test_stats_streak_from_activity_log(client, auth_headers, fixed_now, db):
    headers = auth_headers()
    user_id = _user_id(client, headers)
    for day in ["2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23", "2026-10-02", "2026-10-03"]:
        db.add(ActivityLog(user_id=user_id, date_string=day))
    db.commit()

    # Kolkata "today" is Oct 4: the Oct 2-3 run ended yesterday, so it's current.
    stats = client.get("/api/auth/me/stats", headers={**headers, **KOLKATA}).json()
    assert (stats["current_streak"], stats["highest_streak"]) == (2, 4)


def test_stats_are_empty_for_a_new_user(client, auth_headers, fixed_now):
    stats = client.get("/api/auth/me/stats", headers={**auth_headers(), **KOLKATA}).json()
    assert stats["activity_dates"] == []
    assert (stats["current_streak"], stats["highest_streak"]) == (0, 0)


def d(s: str) -> datetime.date:
    return datetime.date.fromisoformat(s)


@pytest.mark.parametrize(
    "dates, today, expected",
    [
        ([], "2026-10-04", (0, 0)),
        (["2026-10-04"], "2026-10-04", (1, 1)),
        (["2026-10-02", "2026-10-03"], "2026-10-04", (2, 2)),        # ended yesterday: still current
        (["2026-10-01", "2026-10-02"], "2026-10-04", (0, 2)),        # two days ago: broken
        (["2026-09-01", "2026-09-02", "2026-09-03", "2026-10-04"], "2026-10-04", (1, 3)),
        (["2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"], "2026-10-04", (5, 5)),
    ],
)
def test_compute_streaks(dates, today, expected):
    assert compute_streaks([d(x) for x in dates], d(today)) == expected
