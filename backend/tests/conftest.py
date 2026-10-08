"""Shared fixtures. Tests need only a local Postgres: no Groq, HuggingFace or
network. The app's settings are fixed below, before anything imports `app`."""
import json
import os
import shutil
import socket
import tempfile
import uuid
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

_TMP_ROOT = tempfile.mkdtemp(prefix="pathshala-tests-")

# Every Settings field is set explicitly, so a developer's backend/.env (which
# pydantic-settings also reads) can never leak into the tests.
os.environ.update(
    {
        "DATABASE_URL": os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/pathshala_test",
        ),
        "GROQ_API_KEY": "test-placeholder",
        "GROQ_MODEL": "test-model",
        "SECRET_KEY": "test-secret-placeholder-at-least-32-bytes",
        "GOOGLE_CLIENT_ID": "test-client-placeholder",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
        "FRONTEND_URL": "http://localhost:5173",
        "MAX_UPLOAD_MB": "50",
        "EMBEDDING_BACKEND": "fake",
        "UPLOAD_DIR": os.path.join(_TMP_ROOT, "uploads"),
        "CHROMA_PATH": os.path.join(_TMP_ROOT, "chroma"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "ANONYMIZED_TELEMETRY": "False",
        "CHROMA_MODE": "persistent",
        "CHROMA_HOST": "",
        "CHROMA_PORT": "8000",
        "CHROMA_SSL": "false",
        "CHROMA_API_KEY": "",
        "CHROMA_TENANT": "",
        "CHROMA_DATABASE": "",
        "CHROMA_COLLECTION": "pathshala_docs",
        # test_rate_limit.py switches the limiter on for its own tests.
        "RATE_LIMIT_ENABLED": "false",
        "RATE_LIMIT_STORAGE_URI": "",
        "CLIENT_IP_HEADER": "",
        "FRONTEND_DIST_DIR": "",
        "REINDEX_ON_STARTUP": "false",
    }
)

from sqlalchemy.engine import make_url  # noqa: E402

_DB_URL = make_url(os.environ["DATABASE_URL"])
if not (_DB_URL.database or "").endswith("_test"):
    pytest.exit(
        f"Refusing to run: test database {_DB_URL.database!r} does not end in '_test'. "
        "Set TEST_DATABASE_URL to a throwaway database.",
        returncode=2,
    )

import chromadb  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import inspect, text  # noqa: E402

from app.main import app  # noqa: E402
from app.models.database import Base, SessionLocal, engine  # noqa: E402
from app.models import models as _models  # noqa: E402,F401  (registers tables)
from app.services import embedding_service as embedding_service_module  # noqa: E402
from app.services.embedding_service import EmbeddingService, get_embedding_service  # noqa: E402
from app.services.fake_embedder import FakeEmbedder  # noqa: E402
from app.services.llm_service import LLMService, get_llm_service  # noqa: E402

TEST_PASSWORD = "Correct-horse-battery"


# --------------------------------------------------------------------------
# Network guard: anything other than local/Postgres connections fails loudly.
# --------------------------------------------------------------------------

_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "testserver", _DB_URL.host or "localhost"}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    real_connect = socket.socket.connect
    real_getaddrinfo = socket.getaddrinfo

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            host = address[0]
            if host not in _ALLOWED_HOSTS:
                raise RuntimeError(f"Network access blocked in tests: {address!r}")
        return real_connect(sock, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host not in _ALLOWED_HOSTS and host is not None:
            raise RuntimeError(f"DNS lookup blocked in tests: {host!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # Keep pytest's log capture intact.
    cfg.attributes["configure_logger"] = False
    return cfg


def _drop_leftover_tables() -> None:
    """A test DB once built by create_all has tables but no alembic_version,
    so `downgrade base` can't remove them. Start from an empty schema."""
    leftovers = set(inspect(engine).get_table_names()) - {"alembic_version"}
    if leftovers:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    _drop_leftover_tables()
    command.upgrade(cfg, "head")
    yield
    engine.dispose()
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_tables(migrated_db):
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    shutil.rmtree(os.environ["UPLOAD_DIR"], ignore_errors=True)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# --------------------------------------------------------------------------
# Fakes
# --------------------------------------------------------------------------

class FakeGroqClient:
    """Stands in for groq.Groq: `.chat.completions.create(**kwargs)` returns the
    next queued reply (a string, or an exception to raise) and records kwargs."""

    def __init__(self, responses=None):
        self.responses = deque(responses or [])
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def queue(self, *responses) -> None:
        self.responses.extend(responses)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("FakeGroqClient: no queued response")
        reply = self.responses.popleft()
        if isinstance(reply, BaseException):
            raise reply
        prompt_tokens = sum(len(str(m.get("content", "")).split()) for m in kwargs.get("messages", []))
        completion_tokens = len(reply.split())
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )


class FakeLLM:
    """Stands in for LLMService at the method level, recording each call."""

    def __init__(self):
        self.answers: deque = deque()
        self.quizzes: deque = deque()
        self.calls: list[tuple[str, dict]] = []

    def generate_response(self, prompt, context_chunks=None, history=None) -> str:
        self.calls.append(("generate_response", {"prompt": prompt, "context_chunks": context_chunks, "history": history}))
        reply = self.answers.popleft() if self.answers else f"Fake answer to: {prompt}"
        if isinstance(reply, BaseException):
            raise reply
        return reply

    def generate_quiz(self, document_text: str) -> list[dict]:
        self.calls.append(("generate_quiz", {"document_text": document_text}))
        reply = self.quizzes.popleft() if self.quizzes else make_questions()
        if isinstance(reply, BaseException):
            raise reply
        return reply


def make_questions(n: int = 10) -> list[dict]:
    return [
        {
            "question": f"Question {i + 1} about photosynthesis?",
            "options": [f"Option {i}-A", f"Option {i}-B", f"Option {i}-C", f"Option {i}-D"],
            "answer": f"Option {i}-B",
            "explanation": "Because the text says so.",
            "topic": "Biology",
        }
        for i in range(n)
    ]


def make_quiz_json(n: int = 10) -> str:
    return json.dumps({"questions": make_questions(n)})


@pytest.fixture
def fake_groq() -> FakeGroqClient:
    return FakeGroqClient()


@pytest.fixture
def fake_embedding_service():
    """A real EmbeddingService on in-memory Chroma with the hash embedder."""
    chroma = chromadb.EphemeralClient(settings=chromadb.Settings(anonymized_telemetry=False))
    # EphemeralClients share one in-process store, so isolate by collection.
    name = f"test_{uuid.uuid4().hex}"
    service = EmbeddingService(FakeEmbedder(), chroma, collection_name=name)
    yield service
    chroma.delete_collection(name)


@pytest.fixture
def client(fake_groq, fake_embedding_service, monkeypatch):
    app.dependency_overrides[get_llm_service] = lambda: LLMService(client=fake_groq)
    app.dependency_overrides[get_embedding_service] = lambda: fake_embedding_service
    # The background PDF task calls the factory directly, not through Depends.
    monkeypatch.setattr(embedding_service_module, "get_embedding_service", lambda: fake_embedding_service)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def fake_llm(client) -> FakeLLM:
    """Opt in to the method-level fake instead of LLMService + FakeGroqClient."""
    fake = FakeLLM()
    app.dependency_overrides[get_llm_service] = lambda: fake
    return fake


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

@pytest.fixture
def auth_headers(client):
    def _auth_headers(email: str = "student@example.com", password: str = TEST_PASSWORD) -> dict:
        resp = client.post("/api/auth/register", json={"email": email, "password": password, "name": "Test"})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _auth_headers


@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    return (FIXTURES_DIR / "sample.pdf").read_bytes()


@pytest.fixture
def upload_pdf(client, sample_pdf_bytes):
    """Upload a PDF; the background task has finished when this returns."""
    def _upload(headers: dict, data: bytes = None, filename: str = "notes.pdf"):
        return client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": (filename, data if data is not None else sample_pdf_bytes, "application/pdf")},
        )

    return _upload
