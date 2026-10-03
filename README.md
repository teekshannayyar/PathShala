# 📚 PathShala

> **Pathshala** (Hindi: *school*): an AI study assistant that answers questions and writes quizzes from your own PDFs.

[![CI](https://github.com/teekshannayyar/PathShala/actions/workflows/ci.yml/badge.svg)](https://github.com/teekshannayyar/PathShala/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql)](https://postgresql.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.x-orange)](https://www.trychroma.com)
[![Groq](https://img.shields.io/badge/LLM-Groq-f55036)](https://groq.com)

---

## ✨ What is PathShala?

PathShala is a **RAG (retrieval-augmented generation) tutor**. You upload a PDF; the backend extracts its text, splits it into chunks, embeds them into a vector store, and then answers your questions using the most relevant chunks as context. It can also turn the document into a multiple-choice quiz and track which topics you get wrong.

| Feature | What it actually does |
|---------|-----------------------|
| 📄 **PDF upload** | PDF only (extension, content type and `%PDF-` header are checked), up to `MAX_UPLOAD_MB` (50 MB by default). Text extraction and embedding run in the background; each document shows `processing`, `ready` or `failed`, and a failed or stuck document can be **reprocessed**. |
| 💬 **RAG chat** | Ask about an open document: the 3 most relevant chunks plus the last few messages go to the LLM, which is told to answer only from that context. History is saved per document. Without a document open you get a general tutor chat that isn't saved. Answers render as Markdown (no raw HTML). |
| ❓ **Quizzes** | 10 multiple-choice questions (4 options each, with a topic and an explanation) from the first 15,000 characters of the document. Invalid LLM output is retried once. Submitting scores one answer per question and shows the correct answers and explanations. |
| 📊 **Progress** | Dashboard with document count, active chats and study streaks (current and best, counted in your local timezone), attempt counts per quiz, and a "weak topics" list (topics under 60% accuracy). |
| 🗂️ **Document manager** | Folders, rename, single and bulk delete (files and vectors are removed too). |
| 🔐 **Accounts** | Email + password or Google sign-in, JWT sessions, change name, change or set a password, delete account (removes all files, vectors and rows). |
| 📱 **Mobile** | The layout works down to phone widths. |

---

## 🏗️ Architecture

```
Browser ── React 19 + Vite (dev server on :5173)
   │  axios, Authorization: Bearer <JWT>, X-Timezone: <IANA zone>
   ▼
FastAPI (uvicorn on :8000) ── /api/auth  /api/documents  /api/chat  /api/quizzes  /health
   ├── PostgreSQL (SQLAlchemy 2, schema managed by Alembic)
   ├── Chroma vector store (CHROMA_MODE: persistent | http | cloud | ephemeral)
   ├── Embeddings: sentence-transformers all-MiniLM-L6-v2 on CPU
   │               (or EMBEDDING_BACKEND=fake: deterministic hash embedder, no download)
   ├── LLM: Groq API, default model openai/gpt-oss-20b (GROQ_MODEL)
   ├── PDF text: pdfplumber; uploads stored on disk in UPLOAD_DIR
   └── Per-IP rate limits: slowapi
```

- **Chroma modes:** `persistent` stores vectors on disk at `CHROMA_PATH` (the default); `http` talks to a Chroma server (`CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, optional `CHROMA_API_KEY` sent as `x-chroma-token`); `cloud` uses Chroma Cloud (`CHROMA_API_KEY`, optional `CHROMA_TENANT` / `CHROMA_DATABASE`); `ephemeral` keeps everything in memory and loses it on restart. A missing required setting stops the app at startup with a clear error.
- **Embeddings** are computed by the app and passed to Chroma, so Chroma never downloads its own model. The sentence-transformers model is downloaded on first use (about 90 MB) and needs roughly 1 GB of RAM together with torch.
- **Streaks** use the browser's timezone, sent on every request as `X-Timezone`; a missing or invalid value falls back to UTC.

---

## 🚀 Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+ (CI uses 20)
- PostgreSQL 14+ (CI uses 16)
- A [Groq API key](https://console.groq.com/keys)
- Optional: a Google OAuth client ID, for "Sign in with Google"

### 1. Clone

```bash
git clone https://github.com/teekshannayyar/PathShala.git
cd PathShala
```

### 2. Backend (http://127.0.0.1:8000)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
cp .env.example .env               # then edit .env (see the table below)
createdb pathshala                 # or: psql -c 'CREATE DATABASE pathshala'
alembic upgrade head               # create or upgrade the schema
uvicorn app.main:app --reload
```

- The `--extra-index-url` installs the CPU-only torch build, which is much smaller than the default CUDA one. It is optional.
- In `.env`, set at least `DATABASE_URL`, `GROQ_API_KEY` and `SECRET_KEY`. `GOOGLE_CLIENT_ID` must be present but can stay a placeholder if you don't use Google sign-in.
- To run without downloading the embedding model (offline work, quick checks), set `EMBEDDING_BACKEND=fake`. Retrieval quality is much lower.
- The app never creates tables on startup: run `alembic upgrade head` after every pull that adds a migration.
- Check it's up: `curl http://127.0.0.1:8000/health`. Interactive API docs are at http://127.0.0.1:8000/docs.

**Upgrading a database created before Alembic** (by the old create-tables-on-startup code): run this once from `backend/`, then use `alembic upgrade head` as usual.

```bash
alembic stamp 0001_baseline && alembic upgrade head
```

### 3. Frontend (http://localhost:5173)

In a second terminal, from the repo root:

```bash
cd frontend
npm install
cp .env.example .env.local         # VITE_API_URL and VITE_GOOGLE_CLIENT_ID
npm run dev
```

Without `VITE_GOOGLE_CLIENT_ID` the Google buttons are hidden and email sign-in still works. The backend's `FRONTEND_URL` must include the frontend's origin (`http://localhost:5173` by default) or the browser blocks requests with a CORS error.

---

## 🧪 Tests

The backend suite (130 tests) needs only a local Postgres: no Groq, no Hugging Face, no network.

```bash
cd backend
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-dev.txt
createdb pathshala_test
TEST_DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/pathshala_test pytest -q
```

- `TEST_DATABASE_URL` is read from the shell, not from `.env`. Without it the suite uses `postgresql+psycopg2://postgres:postgres@localhost:5432/pathshala_test`.
- The database name **must end in `_test`**; the suite refuses to run otherwise, because it rebuilds the schema with Alembic and empties every table between tests.
- Every app setting is fixed by `tests/conftest.py`, so your `backend/.env` never leaks in. Groq is replaced by a fake client, embeddings use the deterministic `FakeEmbedder`, and outbound connections are blocked.

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

### CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every pull request and on pushes to `master`:

- **backend:** Python 3.11, a Postgres 16 service, CPU-only torch, `EMBEDDING_BACKEND=fake`, `pytest -q`.
- **frontend:** Node 20, `npm ci`, `npm run lint`, `npm run build`.

---

## ☁️ Deployment (summary)

Nothing is deployed by this repo; it contains the config to do so. See the Deployment section of [HANDOFF.md](HANDOFF.md) for details.

- **API, Docker:** [`backend/Dockerfile`](backend/Dockerfile) (Python 3.11 slim, CPU torch, model pre-downloaded unless `--build-arg PRELOAD_MODEL=false`). On start it runs `alembic upgrade head`, then uvicorn on `$PORT` (default 8000) with proxy headers so rate limits see the real client IP.
  ```bash
  docker build -t pathshala-api backend
  docker run --env-file backend/.env -p 8000:8000 pathshala-api
  ```
  Inside a container `localhost` is the container itself, so point `DATABASE_URL` at a reachable host (on Linux, add `--network host` instead of `-p 8000:8000` to use the host's Postgres).
- **API, Render:** [`render.yaml`](render.yaml) is a Blueprint for the Docker service with a health check on `/health`, a 1 GB disk at `/var/data` (uploads and Chroma), an optional managed Postgres, and every secret as `sync: false`.
- **Frontend, Vercel:** [`frontend/vercel.json`](frontend/vercel.json) rewrites every path to `index.html`, so deep links like `/quizzes` survive a refresh. Set `VITE_API_URL` and `VITE_GOOGLE_CLIENT_ID` in the Vercel project (they're baked in at build time).
- **Google OAuth:** add the production frontend origin to the OAuth client's *Authorized JavaScript origins*, and to the API's `FRONTEND_URL`.
- **Memory:** sentence-transformers plus torch need about 1 GB of RAM, so very small instances run out of memory on the first upload. `render.yaml` uses the `standard` plan for that reason.

---

## ⚙️ Environment variables

No real values belong in this file or in git. `backend/.env` and `frontend/.env*` are git-ignored; the `.env.example` files hold placeholders only.

### Backend (`backend/.env`, read by `app/core/config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *required* | SQLAlchemy URL, e.g. `postgresql+psycopg2://USER:PASSWORD@localhost:5432/pathshala`. Alembic reads it too. |
| `GROQ_API_KEY` | *required* | Groq API key. Any placeholder lets the app start, but chat and quizzes then fail with 502. |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Groq model used for chat and quiz generation. |
| `SECRET_KEY` | *required* | Signs JWTs (HS256). Use a long random string. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime. |
| `GOOGLE_CLIENT_ID` | *required* | Google OAuth client ID that ID tokens are verified against. A placeholder is fine if Google sign-in is unused. |
| `FRONTEND_URL` | `http://localhost:5173` | Comma-separated allowed CORS origins; trailing slashes are ignored. |
| `UPLOAD_DIR` | `./uploads` | Where uploaded PDFs are stored. Needs a persistent disk in production. |
| `MAX_UPLOAD_MB` | `50` | Maximum PDF size. |
| `EMBEDDING_BACKEND` | `sentence-transformers` | `fake` swaps in a deterministic hash embedder (no model download; lower quality). |
| `CHROMA_MODE` | `persistent` | `persistent`, `http`, `cloud` or `ephemeral`. |
| `CHROMA_PATH` | `./chroma_data` | On-disk store for `persistent` mode. |
| `CHROMA_COLLECTION` | `pathshala_docs` | Collection name. |
| `CHROMA_HOST` | *(none)* | Chroma server host; required for `http` mode. |
| `CHROMA_PORT` | `8000` | Chroma server port (`http` mode). |
| `CHROMA_SSL` | `false` | Use HTTPS to the Chroma server (`http` mode). |
| `CHROMA_API_KEY` | *(none)* | Required for `cloud`; optional `x-chroma-token` for `http`. |
| `CHROMA_TENANT` | *(none)* | Chroma Cloud tenant (`cloud` mode, optional). |
| `CHROMA_DATABASE` | *(none)* | Chroma Cloud database (`cloud` mode, optional). |
| `RATE_LIMIT_ENABLED` | `true` | Turns the per-IP rate limits on or off. |
| `RATE_LIMIT_STORAGE_URI` | *(empty = in-process memory)* | Shared counter store, e.g. `redis://host:6379` (needs the `redis` package, not installed by default). |
| `PORT` | `8000` | Docker image only: port uvicorn listens on (Render sets it). |
| `FORWARDED_ALLOW_IPS` | `*` | Docker image only: proxies uvicorn trusts for `X-Forwarded-For`. |
| `TEST_DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/pathshala_test` | Tests only, read from the shell. Database name must end in `_test`. |

### Frontend (`frontend/.env.local`, read at build time)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend base URL, without `/api`. |
| `VITE_GOOGLE_CLIENT_ID` | *(empty: Google sign-in hidden)* | Same OAuth client ID as the backend's `GOOGLE_CLIENT_ID`. |

---

## 📁 Project structure

```
PathShala/
├── .github/workflows/ci.yml   # backend tests + frontend lint/build
├── render.yaml                # Render Blueprint for the API
├── backend/
│   ├── Dockerfile, .dockerignore
│   ├── alembic.ini, alembic/versions/   # 0001 baseline, 0002 processing status, 0003 quiz explanations
│   ├── app/
│   │   ├── main.py            # app, CORS, rate limiter, routers, /health
│   │   ├── core/              # config, rate limits, timezone helpers
│   │   ├── api/routes/        # auth, documents, chat, quizzes
│   │   ├── models/            # SQLAlchemy models, session, schemas
│   │   └── services/          # PDF, embeddings, LLM, quiz parser, uploads, activity
│   ├── tests/                 # pytest suite (fakes, no network)
│   ├── requirements.txt, requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # routes and session handling
│   │   ├── api.js             # every API call (axios)
│   │   └── components/        # pages and UI pieces
│   ├── vercel.json
│   └── .env.example
├── HANDOFF.md                 # developer handoff: endpoints, models, known issues, roadmap
└── README.md
```

---

## 🛠️ Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, React Router 7, axios, react-markdown + remark-gfm, lucide-react, react-hot-toast, @react-oauth/google |
| Backend | FastAPI, Python 3.11, SQLAlchemy 2, Alembic, pydantic-settings, slowapi |
| Database | PostgreSQL |
| Vector store | ChromaDB 1.x |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| LLM | Groq API, `openai/gpt-oss-20b` by default |
| Auth | PyJWT, bcrypt, google-auth |
| PDF parsing | pdfplumber |
| Deployment config | Docker, Render, Vercel |

---

## 📖 More

- [HANDOFF.md](HANDOFF.md): API endpoints, frontend routes, data models, rate limits, known issues and roadmap.
- API reference: http://127.0.0.1:8000/docs while the backend is running.
- The repository is public. There is no LICENSE file yet, so no open-source license has been granted.
