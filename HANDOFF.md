# PathShala Developer Handoff

> **Last updated:** October 3, 2026
> **Status:** working MVP; deployment config ready, not deployed
> **Repository:** https://github.com/teekshannayyar/PathShala (**public**)

Setup, tests and the full environment variable reference live in [README.md](README.md). This file covers how the code is put together, what each endpoint and table does, what's known to be wrong, and what comes next.

---

## 📌 What is PathShala?

A PDF-based AI study assistant (a RAG app). Users upload study PDFs, then:

- chat with a document, with answers grounded in its most relevant passages (Groq, default model `openai/gpt-oss-20b`)
- generate 10-question multiple-choice quizzes with explanations, take them, and see weak topics
- track study streaks in their own timezone
- organise documents into folders, rename them, bulk-delete them, and reprocess failed ones

**Design theme:** warm white background (`#fffdfa`), orange accent (`#ea580c`), Inter font. Works on phone widths. Follow the design rules below.

---

## Design rules

The project owner's rules for the website. Every change to the frontend must follow them:

- Never use purple gradients.
- Never use pill-shaped buttons.
- No fake reviews.
- No fake metrics.
- No vague hero text.
- No emoji icons.
- No em dashes.
- No over-the-top scroll animation.
- Never use AI-slop photos.
- Never use AI-slop copy.
- No cursor animation.
- No fake customer counters.
- Make no mistakes and follow precisely.

In practice: buttons, badges and inputs use small corner radii (`--radius-sm`, 8px, or less); only icon-only circular buttons and avatars are round. Icons come from `lucide-react`. Every number shown in the app is computed from the user's own data. Animations are short (about 0.2 s) fades or slides for pages, menus and modals; nothing reacts to scrolling or follows the cursor. Copy says plainly what the app does.

---

## Pre-launch checklist

Do not launch until every item is done:

- [ ] Connect a custom domain.
- [ ] Add a favicon. Done in code (`frontend/public/favicon.svg`, an orange "P" linked from `frontend/index.html`); confirm it shows on the custom domain.
- [ ] Remove any "Made with AI" tag. Checked on October 3, 2026 in `frontend/src`, `frontend/index.html`, `frontend/public` and the rest of the repository: none was found. Check the live site again after deploying.
- [ ] Finalize the Privacy Policy page (`/privacy`, `frontend/src/components/PrivacyPolicy.jsx`). It is a draft: fill in every placeholder in square brackets (operator name, contact email, effective date, hosting providers, logs, backups and the other marked items) and have it reviewed.
- [ ] Finalize the Terms and Conditions page (`/terms`, `frontend/src/components/TermsPage.jsx`). It is also a draft with placeholders in square brackets to fill in and review.

---

## 🏗️ Architecture

```
PathShala/
├── .github/workflows/ci.yml       # backend pytest + frontend lint/build
├── render.yaml                    # Render Blueprint (API service, disk, optional Postgres)
├── frontend/                      # React 19 + Vite 8 (dev server on port 5173)
│   ├── vercel.json                # SPA rewrites for deep links
│   └── src/
│       ├── App.jsx                # routes, session restore, open-document state
│       ├── api.js                 # every API call; adds Bearer token + X-Timezone; 401 → session-expired event
│       ├── index.css              # global CSS variables / design tokens
│       └── components/
│           ├── Auth.jsx/.css             # login, signup, Google sign-in
│           ├── LandingPage.jsx/.css      # public landing page
│           ├── Navbar.jsx/.css           # top navigation (logged in)
│           ├── Sidebar.jsx/.css          # document list on /chat, upload, polls every 5 s
│           ├── Dashboard.jsx/.css        # stats cards + recent documents
│           ├── ChatInterface.jsx/.css    # RAG chat, Markdown rendering (no raw HTML)
│           ├── DocumentManager.jsx/.css  # folders, rename, delete, bulk delete, reprocess
│           ├── QuizHub.jsx/.css          # generate quizzes, quiz list, weak topics
│           ├── QuizTaker.jsx/.css        # take a quiz, results with explanations
│           ├── ProfileSettings.jsx/.css  # name, password, delete account
│           ├── LegalPage.jsx/.css        # shared layout and draft note for the legal pages
│           ├── PrivacyPolicy.jsx         # /privacy (draft)
│           └── TermsPage.jsx             # /terms (draft)
│
└── backend/                       # FastAPI (uvicorn on port 8000)
    ├── Dockerfile, .dockerignore
    ├── alembic/versions/          # 0001_baseline, 0002_document_processing_status, 0003_question_explanation
    ├── tests/                     # pytest suite, fakes only, no network
    └── app/
        ├── main.py                # app, CORS (outermost), slowapi limiter, routers, /health
        ├── core/
        │   ├── config.py          # pydantic Settings (reads backend/.env)
        │   ├── rate_limit.py      # limiter + per-route limits + 429 handler
        │   └── timezone.py        # X-Timezone parsing, local dates (UTC fallback)
        ├── models/
        │   ├── database.py        # engine, SessionLocal, get_db
        │   ├── models.py          # all tables
        │   └── schemas.py         # DocumentResponse
        ├── api/
        │   ├── deps.py            # get_owned_document (404 for missing *and* not yours)
        │   └── routes/            # auth.py, documents.py, chat.py, quizzes.py
        └── services/
            ├── pdf_service.py         # pdfplumber extraction, 500-word chunks (100 overlap), background processing
            ├── embedding_service.py   # embedder choice, Chroma client factory (4 modes), search/upsert/delete
            ├── fake_embedder.py       # deterministic hash embedder (EMBEDDING_BACKEND=fake, tests)
            ├── llm_service.py         # Groq wrapper: chat answer, quiz generation with one retry
            ├── quiz_parser.py         # validates the quiz JSON (10 questions, 4 distinct options, answer in options)
            ├── upload_service.py      # PDF checks + streamed save under a random name
            └── activity_service.py    # record_activity: marks today (user's timezone) as a study day
```

**Request flow for a chat question:** ownership check → activity logged for today → user message saved → last 4 earlier messages loaded as memory → top 3 chunks from Chroma (filtered by `document_id`) → Groq → assistant message saved. Without a `document_id` it's a plain tutor chat with no context and nothing saved.

**Upload flow:** validate and stream the PDF to `UPLOAD_DIR` → `documents` row with `processing_status="processing"` → FastAPI `BackgroundTasks` runs `PDFService.process_document` in the same process → `ready` (text stored, chunks embedded) or `failed` (with `processing_error`, e.g. a scanned PDF with no text).

---

## ⚙️ Configuration

All settings are in `backend/app/core/config.py` and documented, with defaults, in the "Environment variables" table in [README.md](README.md). `backend/.env.example` and `frontend/.env.example` list every one of them with placeholders.

**Never commit `backend/.env` or `frontend/.env.local`.** Both are git-ignored.

Things that trip people up:

- `DATABASE_URL`, `GROQ_API_KEY`, `SECRET_KEY` and `GOOGLE_CLIENT_ID` have no defaults; the app won't import without them. A placeholder `GOOGLE_CLIENT_ID` is fine if Google sign-in is unused.
- `FRONTEND_URL` is a comma-separated CORS allow-list, e.g. `https://pathshala.example.com,http://localhost:5173`.
- `CHROMA_MODE=http` without `CHROMA_HOST`, or `cloud` without `CHROMA_API_KEY`, fails at startup with a message saying so.
- `EMBEDDING_BACKEND=fake` avoids downloading the sentence-transformers model (useful offline and in CI); answers get worse context.

---

## 🚀 Running locally

Full steps are in the README. In short:

```bash
# backend/
cp .env.example .env            # edit it
alembic upgrade head
uvicorn app.main:app --reload   # http://127.0.0.1:8000, docs at /docs

# frontend/
cp .env.example .env.local
npm install
npm run dev                     # http://localhost:5173
```

### Database migrations (Alembic)

The schema is managed only by Alembic; startup never creates or alters tables. Run all commands from `backend/`. Alembic takes `DATABASE_URL` from the app settings (environment, then `backend/.env`), not from `alembic.ini`.

- **Fresh (empty) database:** `alembic upgrade head`
- **Existing database created by the old auto-create startup:** run once, then use `alembic upgrade head` as usual:
  ```bash
  alembic stamp 0001_baseline && alembic upgrade head
  ```
  This works whether or not the step 3 manual `ALTER TABLE documents ...` was run. Migration `0002` adds `processing_status`/`processing_error` only if missing, marks embedded documents `ready`, and marks older unfinished ones `failed` with "Uploaded before processing fix; please reprocess" (use Reprocess on the Documents page). Migration `0003` adds the nullable `questions.explanation`.
- **New schema change:** edit `app/models/models.py`, then `alembic revision --autogenerate -m "describe change"`, review the generated file, and `alembic upgrade head`. `tests/test_migrations.py` fails if the models and the migrations drift apart.

### Tests and offline development

```bash
cd backend
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-dev.txt
createdb pathshala_test
TEST_DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/pathshala_test pytest -q
```

- 133 tests. They need only a local Postgres. The suite rebuilds the test database's schema with Alembic and truncates every table between tests, so `TEST_DATABASE_URL` must name a database ending in `_test`; anything else makes it exit before touching the database.
- `tests/conftest.py` sets every app setting itself before importing the app, so a developer's `backend/.env` can't leak in.
- **Fakes, not network:** the routes get their services through `Depends(get_llm_service)` and `Depends(get_embedding_service)`, and tests swap them with `app.dependency_overrides` for a fake Groq client (canned answers and quiz JSON) and an in-memory Chroma with `FakeEmbedder`. Outbound sockets are blocked, so an accidental real call fails loudly.
- Rate limits are off in tests (`RATE_LIMIT_ENABLED=false`) except in `test_rate_limit.py`.
- CI (`.github/workflows/ci.yml`) runs the same suite against Postgres 16 with `EMBEDDING_BACKEND=fake`, plus `npm run lint` and `npm run build` for the frontend.

---

## 🗄️ Data models (`backend/app/models/models.py`)

| Table | Columns | Notes |
|-------|---------|-------|
| `users` | `id`, `email` (unique), `hashed_password` (null for Google-only), `name`, `picture`, `created_at` | New emails are stored lowercased; lookups are case-insensitive. Deleting a user cascades to everything below. |
| `documents` | `id`, `owner_id` → users, `filename`, `folder` (default `Uncategorized`), `file_path`, `file_size`, `original_text`, `summary`, `key_concepts`, `total_chunks`, `embedding_complete`, `processing_status` (`processing`/`ready`/`failed`), `processing_error`, `created_at`, `updated_at` | `embedding_complete` is kept for compatibility and is true only when `ready`. `summary` and `key_concepts` are never filled in. `owner_id` is nullable for legacy rows. |
| `messages` | `id`, `document_id` → documents, `role` (`user`/`assistant`), `content`, `created_at` | Chat history per document. |
| `activity_logs` | `id`, `user_id` → users, `date_string` (`YYYY-MM-DD`, user's local day), `created_at` | One row per study day; written on upload, chat and quiz submit. |
| `quizzes` | `id`, `document_id` → documents, `user_id` → users, `title`, `created_at` | Title is the document's file name without extension. |
| `questions` | `id`, `quiz_id` → quizzes, `text`, `options` (JSON string), `correct_answer`, `topic`, `explanation` (nullable) | Quizzes made before migration `0003` have no explanations. |
| `quiz_attempts` | `id`, `quiz_id` → quizzes, `user_id` → users, `score`, `total_questions`, `completed_at` | |
| `question_attempts` | `id`, `attempt_id` → quiz_attempts, `question_id` → questions, `user_answer` (null if skipped), `is_correct` | Source for weak-topic analytics. |

Every foreign key is `ON DELETE CASCADE`.

---

## 🧭 Frontend routes (`frontend/src/App.jsx`)

| Path | Access | Page |
|------|--------|------|
| `/` | public (logged-in users go to `/chat`) | Landing page |
| `/login`, `/signup` | public (logged-in users go to `/chat`) | Auth forms with Google sign-in |
| `/dashboard` | logged in | Stats and recent documents |
| `/chat` | logged in | Chat; `?doc=<id>` names the open document, so reloads and links keep it |
| `/documents` | logged in | Document manager |
| `/quizzes` | logged in | Quiz hub; `?generate=<docId>` preselects a ready document (never auto-generates) |
| `/quizzes/take/:id` | logged in | Take a quiz, then see results |
| `/settings` | logged in | Profile name, password, delete account |
| `/privacy` | any | Privacy Policy (draft with placeholders) |
| `/terms` | any | Terms and Conditions (draft with placeholders) |
| `*` | any | Not found page |

Logged-out users on a protected path go to `/login`. The JWT lives in `localStorage`; on load the app calls `/api/auth/me`, and any 401 outside the login/register/Google calls ends the session and shows a toast.

---

## 🔌 API endpoints

All under `/api` except `/health`. "Auth" means `Authorization: Bearer <JWT>`. Documents and quizzes belonging to someone else answer 404, the same as missing ones. Every request may send `X-Timezone` (an IANA zone); it matters for activity logging and `/me/stats`.

**Auth (`/api/auth`)**

| Method | Path | Auth | Limit | Notes |
|--------|------|------|-------|-------|
| POST | `/register` | – | 10/min | `{email, password, name?}`. Valid email required; password 8+ characters, at most 72 bytes. |
| POST | `/login` | – | 10/min | `{email, password}`. One 401 message for every failure, so it doesn't reveal which emails exist. |
| POST | `/google` | – | 10/min | `{credential}` (Google ID token). Creates the user on first sign-in; signs in to an existing account with the same email. |
| GET | `/me` | yes | – | `{id, email, name, picture, has_password, tier}`; `tier` is always `free` for now. |
| PUT | `/me` | yes | – | `{name}`: update display name. |
| PUT | `/me/password` | yes | 10/hour | `{current_password, new_password}`; a Google-only account sets its first password with `{new_password, google_credential}` from a fresh Google sign-in for the same email. Failures are 403. |
| DELETE | `/me` | yes | – | `{password}` (ignored for Google-only accounts). Removes files, vectors and all rows. |
| GET | `/me/stats` | yes | – | `{total_documents, active_chats, current_streak, highest_streak, activity_dates}` in the user's timezone. |

**Documents (`/api/documents`)**

| Method | Path | Auth | Limit | Notes |
|--------|------|------|-------|-------|
| GET | `/` | yes | – | The user's documents, newest first. |
| POST | `/upload` | yes | 20/hour | Multipart `file`. 415 if not a PDF, 413 over `MAX_UPLOAD_MB`. Returns the document with `processing_status="processing"`. |
| DELETE | `/{id}` | yes | – | Deletes file, vectors, row, messages and quizzes. |
| POST | `/{id}/reprocess` | yes | – | Re-runs extraction and embedding. 409 if still processing (unless stuck for 10+ minutes), 410 if the PDF file is gone. |
| PUT | `/{id}/rename` | yes | – | `{filename}`, 1–255 characters after trimming. |
| PUT | `/{id}/folder` | yes | – | `{folder}`, 1–100 characters after trimming. |
| POST | `/bulk-delete` | yes | – | `{document_ids: [...]}`; ignores ids the user doesn't own. |

**Chat (`/api/chat`)**

| Method | Path | Auth | Limit | Notes |
|--------|------|------|-------|-------|
| POST | `/` | yes | 30/min | `{question, document_id?}`; question 1–4000 characters. Returns `{answer, sources}`. 502 if Groq fails. |
| GET | `/history/{document_id}` | yes | – | Messages, oldest first. |

**Quizzes (`/api/quizzes`)**

| Method | Path | Auth | Limit | Notes |
|--------|------|------|-------|-------|
| POST | `/generate/{document_id}` | yes | 10/hour | 409 while processing, 422 with no extracted text, 502 if the LLM output is unusable twice. Returns `{quiz_id, title}`. |
| GET | `/` | yes | – | Quizzes with attempt counts, newest first. |
| GET | `/{quiz_id}` | yes | – | Questions and options, without answers. |
| POST | `/{quiz_id}/submit` | yes | – | `{answers: [{question_id, user_answer}]}`; one answer per question of this quiz, else 400. Returns score and per-question `correct_answer` and `explanation`. |
| GET | `/analytics/weak-topics` | yes | – | Topics under 60% accuracy, weakest first. |

**Other:** `GET /health` → `{status, llm_provider, model}` (used by Render's health check).

### Rate limits

slowapi, keyed by client IP (`app/core/rate_limit.py`): register/login/Google 10 per minute, password change 10 per hour, chat 30 per minute, quiz generation 10 per hour, upload 20 per hour. Over the limit the API answers 429 with a readable `detail`, and CORS headers are still present so the browser shows the message. Counters live in process memory unless `RATE_LIMIT_STORAGE_URI` points at Redis. The key is the `CLIENT_IP_HEADER` request header when set (first value), else the connection's peer address. Behind a proxy, set `CLIENT_IP_HEADER` to a header the proxy always overwrites (`render.yaml` uses `cf-connecting-ip`), or every user shares the proxy's IP. Don't key on `X-Forwarded-For` with all proxies trusted: proxies append to it, so its left-most entry is whatever the client sent.

---

## ☁️ Deployment

Config only; nothing has been deployed.

- **Docker (`backend/Dockerfile`):** `python:3.11-slim`, CPU-only torch, `all-MiniLM-L6-v2` baked in (skip with `--build-arg PRELOAD_MODEL=false`). The container runs `alembic upgrade head`, then uvicorn on `${PORT:-8000}` with `--proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-127.0.0.1}"`. Widen `FORWARDED_ALLOW_IPS` only to your proxy's addresses, never `*`, and set `CLIENT_IP_HEADER` for rate limits behind an edge proxy.
  ```bash
  docker build -t pathshala-api backend
  docker run --env-file backend/.env -p 8000:8000 pathshala-api
  ```
- **Render (`render.yaml`):** Docker web service rooted at `backend/`, `healthCheckPath: /health`, `standard` plan, a 1 GB disk at `/var/data` with `UPLOAD_DIR=/var/data/uploads` and `CHROMA_PATH=/var/data/chroma`, `CLIENT_IP_HEADER=cf-connecting-ip` (Render's Cloudflare edge overwrites that header, so it's the real client IP), and an optional managed Postgres on the paid `basic-256mb` plan wired into `DATABASE_URL` (Render's free Postgres expires after 30 days; resize as needed). `GROQ_API_KEY`, `SECRET_KEY`, `GOOGLE_CLIENT_ID` and `FRONTEND_URL` are `sync: false`, so Render asks for them and they never live in the repo.
- **Vercel (`frontend/vercel.json`):** rewrites everything to `/index.html`. Set `VITE_API_URL` (the API's public URL) and `VITE_GOOGLE_CLIENT_ID` in the Vercel project settings; they're compiled in at build time, so redeploy after changing them.
- **Google OAuth:** add the production frontend origin (e.g. `https://pathshala.vercel.app`) to *Authorized JavaScript origins* on the OAuth client, and to the API's `FRONTEND_URL`.
- **Memory:** torch plus the embedding model need about 1 GB of RAM; 512 MB instances can run out of memory on the first upload. Use a bigger plan, or `EMBEDDING_BACKEND=fake` only for demos.
- **Disk:** uploads and persistent-mode Chroma need a persistent disk. A Render disk attaches to a single instance, so scaling out means `CHROMA_MODE=http`/`cloud` plus shared file storage (see Known issues).

---

## ✅ Implemented

- Email/password and Google sign-in, JWT sessions (60 minutes by default), session restore on reload, automatic logout on expiry
- Case-insensitive email handling, generic login errors, deleted users' tokens rejected
- Profile: change name, change password, Google-only accounts set a password after re-verifying with Google, delete account with full cleanup
- PDF upload with strict validation and size limit, background processing with visible status, reprocess for failed or stuck documents
- RAG chat with per-document history and short conversational memory; Markdown answers without raw HTML
- Quiz generation (10 MCQs with topics and explanations, validated, one retry), taking, scoring, results with explanations, weak topics
- Study streaks and activity in the user's timezone
- Document manager: folders, rename, delete, bulk delete
- Per-IP rate limits, multi-origin CORS, four Chroma modes
- Alembic migrations, 133 offline tests, CI, Docker/Render/Vercel config
- Phone-width layout, 404 page, toasts and confirmation modals
- PathShala favicon and meta description; public Privacy Policy and Terms and Conditions pages (drafts, see the pre-launch checklist)

---

## 🛠️ Known issues & gotchas

1. **Legacy case-duplicate accounts:** two old accounts whose emails differ only by case can exist; login uses the oldest. Check for duplicates before adding a unique index on `lower(email)`.
2. **No email verification:** anyone can register with someone else's email. Because Google sign-in attaches to an existing account with the same email, the real owner signing in with Google takes over a password account registered under their address, and vice versa. Fixing this needs email verification (see *Later: Email*).
3. **JWTs are not revoked:** changing the password (or, later, resetting it) leaves existing tokens valid until they expire. There is no token versioning; tokens also live in `localStorage`.
4. **torch memory on small hosts:** sentence-transformers and torch need about 1 GB of RAM; small instances crash on the first upload. The model also downloads on first use unless it was baked into the image, so that first upload is slow.
5. **In-memory rate-limit storage:** counters are per process and reset on restart. With several workers or instances each has its own counters, so the real limit multiplies. Set `RATE_LIMIT_STORAGE_URI=redis://...` (and install `redis`) for shared counters.
6. **Uploads need a persistent disk:** PDFs are stored on the local filesystem (and so are vectors in `persistent` Chroma mode). On an ephemeral filesystem they disappear on redeploy, which breaks reprocessing and leaves chat without context. Multiple instances can't share a Render disk.
7. **Background processing is in-process:** a restart mid-processing leaves the document in `processing`; Reprocess accepts it once it's been untouched for 10 minutes. There's no job queue or retry.
8. **Password rules differ:** the signup form asks for an uppercase letter and a symbol, but the API only enforces 8+ characters and at most 72 bytes.
9. **Quizzes see only the start of a document:** generation uses the first 15,000 characters of the extracted text.
10. **Unused columns:** `documents.summary` and `documents.key_concepts` exist but nothing fills them; `/me` returns `tier: "free"` as a placeholder for billing.
11. **Chats without a document aren't saved.**
12. **Vite import errors after a fresh install:** if `react-markdown` imports fail, delete `frontend/node_modules/.vite` and restart `npm run dev`.

---

## 🗺️ Roadmap

### Next (small, unblocks production)

- Shared rate-limit storage (Redis) once there's more than one worker
- Token versioning on `users` so password changes revoke old sessions
- Server-side password strength matching the signup form
- Unique index on `lower(email)` after cleaning up legacy duplicates
- Object storage for uploads and Chroma Cloud/HTTP for vectors, so the API can scale past one instance
- A real job queue for PDF processing

### Later

Planned and designed, not built yet. Nothing below exists in the code.

#### 1. Monetization

- **Free tier:** 50,000 tokens per month (`FREE_TIER_MONTHLY_TOKENS=50000`); premium unlimited (`PREMIUM_TIER_MONTHLY_TOKENS=0`).
- **Token counting:** `llm_service` returns Groq's `completion.usage` (prompt, completion, total tokens). Chat records the call's `total_tokens`; quiz generation records the tokens of both attempts, even when generation fails.
- **Schema:** new `users` columns `tier` (`free`/`premium`), `tokens_used`, `token_reset_date`, `stripe_customer_id` (unique), `stripe_subscription_id`, in a new migration.
- **Enforcement:** a `check_quota` dependency on `POST /api/chat/` and `POST /api/quizzes/generate/{id}` runs after ownership checks and before any LLM call. Over the limit → 402 `{code: "TOKEN_LIMIT_REACHED", tokens_used, limit, reset_date}`. Usage is added with an atomic `UPDATE ... SET tokens_used = tokens_used + n` after the call. Usage resets on the first of each month (UTC). It's a pre-check, so one request can overshoot slightly.
- **Payments:** Stripe or Razorpay checkout plus a signed webhook.
  - `GET /api/payments/usage`: tier, tokens used, limit, reset date (works with payments unconfigured).
  - `POST /api/payments/create-checkout-session` (auth): a subscription checkout for the configured price, returning to `/settings?tab=billing&checkout=success|cancel`; 400 if already premium.
  - `POST /api/payments/webhook` (no auth, exempt from rate limits): verify the signature on the raw body; checkout completed → `premium`; subscription updated → `premium` if active/trialing, else `free`; subscription deleted → `free`. Idempotent; bad signature → 400.
  - Settings `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID` (or the Razorpay equivalents). Unset → payment endpoints answer 503, while token limits still apply.
- **Frontend:** a Billing tab in `/settings` (tier, usage progress bar or "Unlimited", reset date, Upgrade button), and an upgrade modal opened by an `api.js` interceptor on a 402 `TOKEN_LIMIT_REACHED`; "Payments not available" toast on 503.
- **Open question:** a customer portal (manage or cancel subscription) isn't designed yet.

#### 2. Email via Resend

- **Service:** `email_service.send_email` via Resend when `RESEND_API_KEY` is set; otherwise the email is logged (body only outside production, so reset links never land in production logs). Send failures are logged and never break the request. Settings: `RESEND_API_KEY`, `EMAIL_FROM`, `PASSWORD_RESET_TOKEN_TTL_MINUTES=30`, `APP_ENV`.
- **Forgot / reset password:**
  - New `password_reset_tokens` table: `user_id`, `token_hash` (SHA-256, unique), `expires_at`, `used_at`, `created_at`. The raw token (`secrets.token_urlsafe(32)`) is only ever in the email.
  - `POST /api/auth/forgot-password {email}` always returns the same 200 message, invalidates older tokens, and emails `<frontend>/reset-password?token=...` in the background. Rate limit 5/hour.
  - `POST /api/auth/reset-password {token, new_password}`: single use, expires after 30 minutes, 400 "Invalid or expired reset link" otherwise. Rate limit 10/hour. Should also revoke existing JWTs (known issue 3).
  - Frontend: "Forgot password?" link on login, public `/forgot-password` and `/reset-password` pages.
- **Welcome email** after registration and after a first Google sign-in; a send failure never blocks signup.
- **Email verification:** a verification link at signup and an `email_verified` flag; Google sign-in only attaches to an existing password account once its email is verified. This closes known issue 2.

---

## 🧰 Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, React Router 7 |
| Styling | Vanilla CSS (glassmorphism, CSS custom properties) |
| HTTP client | axios |
| Icons | lucide-react |
| Notifications | react-hot-toast |
| Markdown | react-markdown + remark-gfm (no raw HTML) |
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL, SQLAlchemy 2, Alembic |
| Vector store | ChromaDB 1.x (persistent, http, cloud or ephemeral) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (or the fake embedder) |
| LLM | Groq API, `openai/gpt-oss-20b` by default |
| Auth | PyJWT, bcrypt, google-auth |
| Rate limiting | slowapi |
| PDF parsing | pdfplumber |
| CI / deploy | GitHub Actions, Docker, Render, Vercel |
