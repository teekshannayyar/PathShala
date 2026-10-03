# 📚 PathShala

> **Pathshala** (Hindi: *school*) — An AI-powered student learning platform that helps you study smarter.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)](https://postgresql.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Latest-orange)](https://www.trychroma.com)
[![Mistral](https://img.shields.io/badge/Mistral-7B-blueviolet)](https://mistral.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ What is PathShala?

PathShala is a **RAG-based AI tutor** that grounds every answer in your actual course materials — no hallucinations, no generic ChatGPT responses.

| Feature | Description |
|---------|-------------|
| 📄 **PDF Upload** | Upload lecture notes, textbooks, or slides |
| 🧠 **Smart Summaries** | AI-generated summaries and key concepts |
| ❓ **Auto Quizzes** | MCQ, True/False, and short-answer quizzes |
| 💬 **RAG Chat** | Ask questions, get answers grounded in your docs |
| 📊 **Progress Tracking** | Monitor quiz scores and weak areas |

---

## 🏗️ Architecture

```
React Frontend (Port 3000)
        │
   REST API (axios)
        │
FastAPI Backend (Port 8000)
   ├── PDF Service
   ├── Embedding Service
   ├── LLM Service (Mistral via Ollama)
   ├── Summary Service
   ├── Quiz Service
   └── Chat Service (RAG)
        │
  ┌─────┼──────┐
  │     │      │
PostgreSQL ChromaDB Ollama
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- [Ollama](https://ollama.ai) with Mistral 7B

### 1. Clone & Setup

```bash
git clone https://github.com/teekshannayyar/PathShala.git
cd PathShala
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # Fill in your values
alembic upgrade head         # create/upgrade the schema (see HANDOFF.md for existing DBs)
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # Set VITE_API_URL
npm run dev
```

### 4. Ollama (LLM)

```bash
ollama serve
ollama pull mistral
```

---

## 📁 Project Structure

```
PathShala/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
├── docs/
│   └── implementation_plan.md
└── README.md
```

---

## 📖 Documentation

- [Implementation Plan](docs/implementation_plan.md)
- [API Reference](http://localhost:8000/docs) *(when running locally)*

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Mistral 7B via Ollama |
| Vector DB | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Backend | FastAPI + SQLAlchemy |
| Frontend | React 18 + Vite |
| Database | PostgreSQL |
| Deployment | Railway + Vercel |

---

## 📄 License

MIT © 2024 [teekshannayyar](https://github.com/teekshannayyar)
