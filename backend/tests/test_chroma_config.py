"""CHROMA_MODE picks the vector store client; bad combinations fail at startup."""
import os
import subprocess
import sys
from pathlib import Path

import chromadb
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService, build_chroma_client
from app.services.fake_embedder import FakeEmbedder

BACKEND_DIR = Path(__file__).resolve().parents[1]


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_http_mode_requires_host():
    with pytest.raises(ValidationError, match="CHROMA_MODE=http requires CHROMA_HOST"):
        make_settings(CHROMA_MODE="http", CHROMA_HOST="")


def test_cloud_mode_requires_api_key():
    with pytest.raises(ValidationError, match="CHROMA_MODE=cloud requires CHROMA_API_KEY"):
        make_settings(CHROMA_MODE="cloud", CHROMA_API_KEY="")


def test_unknown_mode_is_rejected():
    with pytest.raises(ValidationError):
        make_settings(CHROMA_MODE="sqlite")


def test_app_refuses_to_start_with_http_mode_and_no_host():
    env = {**os.environ, "CHROMA_MODE": "http", "CHROMA_HOST": ""}
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode != 0
    assert "CHROMA_MODE=http requires CHROMA_HOST" in result.stderr


@pytest.fixture
def recorded(monkeypatch):
    calls = []

    def recorder(name):
        def _make(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name
        return _make

    for name in ("PersistentClient", "HttpClient", "CloudClient"):
        monkeypatch.setattr(chromadb, name, recorder(name))
    return calls


def test_persistent_mode(recorded, tmp_path):
    path = str(tmp_path / "chroma")
    assert build_chroma_client(make_settings(CHROMA_PATH=path)) == "PersistentClient"
    assert recorded == [("PersistentClient", (), {"path": path})]
    assert os.path.isdir(path)


def test_http_mode_passes_token_header(recorded):
    cfg = make_settings(CHROMA_MODE="http", CHROMA_HOST="chroma.internal", CHROMA_PORT=9000, CHROMA_SSL=True, CHROMA_API_KEY="placeholder-token")
    build_chroma_client(cfg)
    assert recorded == [(
        "HttpClient", (),
        {"host": "chroma.internal", "port": 9000, "ssl": True, "headers": {"x-chroma-token": "placeholder-token"}},
    )]


def test_http_mode_without_key_sends_no_headers(recorded):
    build_chroma_client(make_settings(CHROMA_MODE="http", CHROMA_HOST="chroma.internal", CHROMA_API_KEY=""))
    assert recorded[0][2]["headers"] is None


def test_cloud_mode(recorded):
    cfg = make_settings(CHROMA_MODE="cloud", CHROMA_API_KEY="placeholder-key", CHROMA_TENANT="t1", CHROMA_DATABASE="")
    build_chroma_client(cfg)
    assert recorded == [("CloudClient", (), {"tenant": "t1", "database": None, "api_key": "placeholder-key"})]


def test_ephemeral_mode_is_a_working_in_memory_store():
    client = build_chroma_client(make_settings(CHROMA_MODE="ephemeral"))
    service = EmbeddingService(FakeEmbedder(), client, collection_name="test_ephemeral_mode")
    try:
        service.add_chunks(1, ["plants make sugar from light", "the moon orbits the earth"])
        assert service.search("light and plants", n_results=1)[0]["text"] == "plants make sugar from light"
    finally:
        client.delete_collection("test_ephemeral_mode")
