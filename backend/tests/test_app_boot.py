"""The app must import and serve /health without loading any model, vector
store or Groq client (no service is built until a request needs it)."""
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

SCRIPT = """
import sys
from fastapi.testclient import TestClient
import app.main
resp = TestClient(app.main.app).get('/health')
assert resp.status_code == 200, resp.text
heavy = [m for m in ('torch', 'sentence_transformers', 'chromadb') if m in sys.modules]
assert not heavy, heavy
print('ok')
"""


def test_import_and_health_load_no_models_or_clients():
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_network_guard_blocks_outbound_connections():
    import socket

    import pytest

    with pytest.raises(RuntimeError, match="blocked"):
        socket.create_connection(("huggingface.co", 443), timeout=1)
    with pytest.raises(RuntimeError, match="blocked"):
        socket.create_connection(("8.8.8.8", 443), timeout=1)
