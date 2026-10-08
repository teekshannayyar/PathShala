"""One-service preview hosting: the API serving the built frontend, and
re-embedding documents whose vectors were lost with the disk."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.middleware import SlowAPIASGIMiddleware

from app.frontend import mount_frontend
from app.models.models import Document, User
from app.services import embedding_service as embedding_service_module
from app.services.reindex_service import reindex_missing_documents


@pytest.fixture
def site(tmp_path):
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "main.js").write_text("console.log(1)")
    # Bigger than one 64 KB FileResponse chunk.
    (tmp_path / "assets" / "big.js").write_text("x" * 300_000)
    (tmp_path.parent / "secret.txt").write_text("nope")

    # Same middleware setup as app.main, with the limiter switched on.
    app = FastAPI()
    app.state.limiter = Limiter(key_func=lambda request: "test", enabled=True)
    app.add_middleware(SlowAPIASGIMiddleware)

    @app.get("/api/ping")
    def ping():
        return {"pong": True}

    mount_frontend(app, str(tmp_path))
    return TestClient(app)


def test_serves_files_and_falls_back_to_index_for_app_routes(site):
    assert site.get("/").text == "<html>app</html>"
    assert site.get("/assets/main.js").text == "console.log(1)"
    assert site.get("/chat").text == "<html>app</html>"
    assert site.get("/privacy").text == "<html>app</html>"


def test_large_files_arrive_whole_with_rate_limiting_on(site):
    resp = site.get("/assets/big.js")
    assert resp.status_code == 200
    assert len(resp.content) == 300_000


def test_api_routes_win_and_unknown_api_paths_stay_404(site):
    assert site.get("/api/ping").json() == {"pong": True}
    assert site.get("/api/nope").status_code == 404


def test_never_serves_files_outside_the_dist_folder(site):
    resp = site.get("/..%2Fsecret.txt")
    assert "nope" not in resp.text


def test_missing_build_fails_loudly(tmp_path):
    with pytest.raises(RuntimeError, match="index.html"):
        mount_frontend(FastAPI(), str(tmp_path))


def test_reindex_restores_only_missing_vectors(db, fake_embedding_service, monkeypatch):
    monkeypatch.setattr(embedding_service_module, "get_embedding_service", lambda: fake_embedding_service)
    user = User(email="r@example.com", name="R")
    db.add(user)
    db.flush()
    text = "photosynthesis converts light into chemical energy " * 200
    kept = Document(owner_id=user.id, filename="a.pdf", original_text=text, processing_status="ready")
    lost = Document(owner_id=user.id, filename="b.pdf", original_text=text, processing_status="ready")
    failed = Document(owner_id=user.id, filename="c.pdf", processing_status="failed")
    db.add_all([kept, lost, failed])
    db.commit()
    fake_embedding_service.add_chunks(kept.id, ["already here"])

    assert reindex_missing_documents() == 1

    hits = fake_embedding_service.search("photosynthesis", n_results=3, document_id=lost.id)
    assert hits and "photosynthesis" in hits[0]["text"]
    assert fake_embedding_service.collection.get(where={"document_id": kept.id})["documents"] == ["already here"]
    assert reindex_missing_documents() == 0


@pytest.mark.parametrize(
    "given",
    ["postgres://u:p@db.example:5432/app", "postgresql://u:p@db.example:5432/app"],
)
def test_host_database_urls_use_the_installed_driver(given):
    from app.core.config import Settings

    url = Settings(_env_file=None, DATABASE_URL=given).DATABASE_URL
    assert url == "postgresql+psycopg2://u:p@db.example:5432/app"


def test_explicit_driver_urls_are_left_alone():
    from app.core.config import Settings

    given = "postgresql+psycopg2://u:p@localhost/app_test"
    assert Settings(_env_file=None, DATABASE_URL=given).DATABASE_URL == given
