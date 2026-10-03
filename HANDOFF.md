# PathShala — Comprehensive Developer Handoff

> **Last Updated:** October 4, 2026  
> **Project Status:** Active Development (Feature-Complete MVP)  
> **Repository:** https://github.com/teekshannayyar/PathShala (Private)

---

## 📌 What is PathShala?

PathShala is a **PDF-based AI study assistant** (RAG application). Users upload their study PDFs, and the app lets them:
- Chat with the document using an AI powered by Groq (Llama 3.1)
- Generate multiple-choice quizzes from the PDF content
- Track their study streaks, quiz scores, and weak topics
- Organize documents into folders, rename them, and bulk-delete

**Design Theme:** Premium glassmorphism aesthetic — warm white background (#fffdfa), vibrant orange accent (#ea580c), Inter font, smooth animations.

---

## 🏗️ Architecture

`
PathShala/
├── frontend/          # React + Vite (port 5173)
│   └── src/
│       ├── App.jsx              # Root with protected routing & session restore
│       ├── api.js               # All Axios API calls (single source of truth)
│       ├── index.css            # Global CSS variables and design tokens
│       └── components/
│           ├── Auth.jsx/.css         # Login + Signup + Google OAuth
│           ├── LandingPage.jsx/.css  # Public landing page
│           ├── Navbar.jsx/.css       # Top navigation (always visible when logged in)
│           ├── Sidebar.jsx/.css      # Chat session list (chat page only)
│           ├── Dashboard.jsx/.css    # Stats cards + recent docs grid
│           ├── ChatInterface.jsx/.css # Core RAG chat UI with markdown rendering
│           ├── DocumentManager.jsx/.css # Folder/rename/bulk-delete hub
│           ├── QuizHub.jsx/.css      # Quiz dashboard + weak topics analytics
│           ├── QuizTaker.jsx/.css    # Active quiz taking + results UI
│           └── ProfileSettings.jsx   # Account name/password/delete settings
│
└── backend/           # FastAPI + Python (port 8000)
    └── app/
        ├── main.py              # App entrypoint, CORS, router mounting
        ├── core/config.py       # Pydantic settings (reads from .env)
        ├── models/
        │   ├── database.py      # SQLAlchemy engine + session
        │   └── models.py        # All DB models
        ├── api/routes/
        │   ├── auth.py          # Register, Login, Google OAuth, /me, stats
        │   ├── documents.py     # Upload, delete, rename, folder, bulk-delete
        │   ├── chat.py          # RAG chat + history
        │   └── quizzes.py       # Generate, list, submit, weak-topics
        └── services/
            ├── pdf_service.py       # PDF text extraction (pdfplumber)
            ├── embedding_service.py # ChromaDB vector store wrapper
            └── llm_service.py       # Groq API wrapper
`

---

## ⚙️ Environment Variables (backend/.env)

**NEVER commit this file. It is in .gitignore.**

`env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST/DB_NAME
GROQ_API_KEY=gsk_...
SECRET_KEY=any-random-long-string-for-jwt-signing
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
FRONTEND_URL=http://localhost:5173
GROQ_MODEL=llama-3.1-8b-instant
`

---

## 🚀 How to Run Locally

**Backend:**
`ash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Create .env file with the vars above
uvicorn app.main:app --reload
# Runs on http://127.0.0.1:8000
`

**Frontend:**
`ash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
`

### Database migrations (Alembic)

The schema is managed by Alembic. The backend no longer creates tables on startup, so run migrations before the first start and after pulling schema changes. Run all commands from `backend/` (Alembic reads `DATABASE_URL` from `backend/.env`, not from `alembic.ini`).

- **Fresh (empty) database:** `alembic upgrade head`
- **Existing database created by the old auto-create startup:** run once, then use `alembic upgrade head` as usual:
  ```bash
  alembic stamp 0001_baseline && alembic upgrade head
  ```
  This works whether or not you ran the step 3 manual `ALTER TABLE documents ...` command. Migration `0002` adds `processing_status`/`processing_error` only if missing, marks embedded documents `ready`, and marks older unfinished ones `failed` with "Uploaded before processing fix; please reprocess" (use Reprocess in the Documents page).
- **New schema change:** edit `app/models/models.py`, then `alembic revision --autogenerate -m "describe change"`, review the generated file, and `alembic upgrade head`.

### Tests and offline development

```bash
cd backend
pip install -r requirements-dev.txt
createdb pathshala_test
TEST_DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/pathshala_test pytest -q
```

- Tests need only a local Postgres. They rebuild the test database's schema with Alembic and truncate every table between tests, so `TEST_DATABASE_URL` must point at a database whose name ends in `_test` (the suite refuses to run otherwise).
- No network is used: Groq is replaced by a fake client, embeddings use the deterministic `FakeEmbedder`, Chroma runs in memory, and outbound connections are blocked.
- To run the app itself without downloading the embedding model, set `EMBEDDING_BACKEND=fake` in `backend/.env` (retrieval quality is much lower; chat answers still need a real `GROQ_API_KEY`).
- Frontend checks: `cd frontend && npm run lint && npm run build`.

CI (`.github/workflows/ci.yml`) runs the backend tests against a Postgres 16 service and the frontend lint and build on every pull request and on pushes to `master`.

---

## 💾 Database Models

| Model | Key Fields |
|-------|-----------|
| User | id, email, hashed_password (null for Google), name, picture |
| Document | id, owner_id, filename, folder (default: Uncategorized), file_path, embedding_complete |
| Message | id, document_id, role (user/assistant), content |
| ActivityLog | id, user_id, date_string (YYYY-MM-DD local time) — used for streak |
| Quiz | id, document_id, user_id, title |
| Question | id, quiz_id, text, options (JSON string), correct_answer, topic |
| QuizAttempt | id, quiz_id, user_id, score, total_questions |
| QuestionAttempt | id, attempt_id, question_id, user_answer, is_correct |

Cascading deletes: User -> Documents -> Messages/Quizzes. Document -> Messages/Quizzes.

---

## 🗺️ Frontend Routes

| Route | Component | Auth |
|-------|-----------|------|
| / | LandingPage | No |
| /login | Auth | No |
| /signup | Auth | No |
| /dashboard | Dashboard | Yes |
| /chat | ChatInterface | Yes |
| /documents | DocumentManager | Yes |
| /quizzes | QuizHub | Yes |
| /quizzes/take/:id | QuizTaker | Yes |
| /settings | ProfileSettings | Yes |

Auth persistence: On mount, App.jsx validates token via GET /api/auth/me. Valid = restore session. Invalid = clear + redirect to /login.

---

## 🔌 Key API Endpoints

**Auth (/api/auth)**
- POST /register — email/password signup
- POST /login — email/password login
- POST /google — Google OAuth
- GET /me — validate token, return user profile
- GET /me/stats — streak + document + chat counts
- DELETE /me — delete account (requires password)

**Documents (/api/documents)**
- GET / — list user documents
- POST /upload — upload PDF (background embedding)
- DELETE /{id} — delete single doc
- PUT /{id}/rename — rename document
- PUT /{id}/folder — move to folder
- POST /bulk-delete — delete multiple by ID list

**Chat (/api/chat)**
- POST / — RAG chat (body: {question, document_id})
- GET /history/{document_id} — load chat history

**Quizzes (/api/quizzes)**
- POST /generate/{document_id} — AI generates 10-question MCQ quiz
- GET / — list all user quizzes
- GET /{quiz_id} — get quiz with questions
- POST /{quiz_id}/submit — submit answers, get scored results
- GET /analytics/weak-topics — topics with lowest accuracy %

---

## ✅ Fully Implemented Features

- JWT authentication (email + Google OAuth)
- Session persistence on browser refresh
- PDF upload with background ChromaDB embedding pipeline
- RAG Chat with Groq LLM (Llama 3.1 8B)
- Chat history persistence per document
- Markdown rendering in chat (tables, bold, br tags)
- Study streak tracking via ActivityLog (timezone-safe, local time)
- Quiz generation (10 MCQs via LLM from PDF)
- Quiz taking, scoring, attempt history
- Weak topic analytics from incorrect answers
- Document manager: folders, inline rename, bulk-delete with checkboxes
- Account settings: name change, password change, account deletion
- Toast notifications + confirmation modals

---

## 🛠️ Known Issues & Gotchas

1. **Streak Timezone:** ActivityLog uses datetime.now() (local time). Server deployment to UTC will need revisiting.
2. **ChromaDB is local:** Stored in ./chroma_data. Cloud deployment requires migrating to Pinecone or Chroma Cloud.
3. **Rate limiting:** slowapi is installed but not fully applied to all endpoints.
4. **No email verification:** Users can register with any email. No forgot-password flow yet.
5. **react-markdown import error:** If Vite shows import errors after fresh install, clear node_modules/.vite cache and restart dev server.

---

## 🗺️ Roadmap (What to Build Next)

### 1. Monetization (Highest Priority)
- Add fields to User: tier (free/premium), tokens_used, token_reset_date, stripe_customer_id, stripe_subscription_id
- Update llm_service.py to extract token count from Groq response.usage
- Enforce free tier limit (e.g. 50,000 tokens/month) before LLM calls
- Add Stripe checkout endpoint: POST /api/payments/create-checkout-session
- Add Stripe webhook: POST /api/payments/webhook (updates user tier on payment)
- Frontend: Add Billing tab in /settings with token usage progress bar
- Frontend: Show upgrade modal when limit is reached in chat/quiz

### 2. Production Deployment
- Move ChromaDB to Chroma Cloud or Pinecone
- Deploy backend to Render or Railway
- Deploy frontend to Vercel or Netlify
- Set all environment variables in deployment dashboard

### 3. Email Services
- Integrate Resend for transactional emails
- Forgot password flow with reset link
- Welcome email on signup

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 8, React Router 7 |
| Styling | Vanilla CSS (glassmorphism, CSS custom properties) |
| HTTP Client | Axios |
| Icons | Lucide React |
| Notifications | react-hot-toast |
| Markdown | react-markdown + remark-gfm + rehype-raw |
| Backend | FastAPI, Python 3.11+ |
| Database | PostgreSQL + SQLAlchemy ORM |
| Vector Store | ChromaDB (local filesystem) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | Groq API (Llama 3.1 8B Instant) |
| Auth | PyJWT + google-auth (Google OAuth) |
| PDF Parsing | pdfplumber |
