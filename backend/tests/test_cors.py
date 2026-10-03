"""FRONTEND_URL is a comma-separated origin list. CORS is configured when
app.main is imported, so the app is checked in a fresh interpreter."""
import json
import os
import subprocess
import sys
from pathlib import Path

from app.core.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]

SCRIPT = """
import json, sys
from fastapi.testclient import TestClient
import app.main
client = TestClient(app.main.app)
out = {}
for origin in sys.argv[1:]:
    get = client.get('/health', headers={'Origin': origin})
    pre = client.options('/api/auth/login', headers={
        'Origin': origin,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type,x-timezone',
    })
    out[origin] = {
        'get': get.headers.get('access-control-allow-origin'),
        'preflight_status': pre.status_code,
        'preflight': pre.headers.get('access-control-allow-origin'),
    }
print(json.dumps(out))
"""


def test_each_listed_origin_is_allowed_and_others_are_not():
    env = {**os.environ, "FRONTEND_URL": "https://a.example/, http://localhost:5173"}
    origins = ["https://a.example", "http://localhost:5173", "https://evil.example"]
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, *origins],
        cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout.strip().splitlines()[-1])

    for allowed in origins[:2]:
        assert out[allowed] == {"get": allowed, "preflight_status": 200, "preflight": allowed}
    assert out["https://evil.example"]["get"] is None
    assert out["https://evil.example"]["preflight"] is None
    assert out["https://evil.example"]["preflight_status"] == 400


def test_cors_origins_parsing():
    s = Settings(_env_file=None, FRONTEND_URL=" https://a.example/ ,,http://localhost:5173,")
    assert s.cors_origins == ["https://a.example", "http://localhost:5173"]
