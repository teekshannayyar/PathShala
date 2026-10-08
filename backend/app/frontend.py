from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

# Paths the API owns. Anything else is a page of the single-page app.
API_PREFIXES = ("api/", "health", "docs", "redoc", "openapi.json")


def mount_frontend(app: FastAPI, dist_dir: str) -> None:
    """Serve the built web app from dist_dir: real files as they are, every
    other non-API path as index.html so deep links like /chat load the app.
    Must be called after the API routers are included."""
    root = Path(dist_dir).resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"FRONTEND_DIST_DIR={dist_dir!r} has no index.html; build the frontend first")

    @app.get("/{path:path}", include_in_schema=False)
    def serve_frontend(path: str):
        if path.startswith(API_PREFIXES):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    # slowapi's ASGI middleware re-sends the response start for every body
    # chunk, which breaks files streamed in more than one chunk (over 64 KB).
    # Exempt routes bypass it, and static files need no rate limit anyway.
    limiter = getattr(app.state, "limiter", None)
    if limiter is not None:
        limiter.exempt(serve_frontend)
