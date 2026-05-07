# Vibe — Music-First Dating App

Match through music. Photos stay hidden until you both like each other.

---

## Team

| Name | Role |
|---|---|
| Jack Escowitz | Auth + User Profile (Backend) |
| Michael Miao | Spotify Integration + Background Refresh (Backend) |
| Sarah Randhawa | Matching Algorithm + Feed + Likes + Matches (Backend) |
| Angelina Wu | Frontend (Flask) |
| Aryaman Nagpal | Infrastructure (DevOps + MongoDB) |

---
## Live Demo

**URL:** http://174.138.42.115:3000

**Demo accounts (no Spotify required — music data pre-seeded):**

| Email | Password |
|---|---|
| `admin1@nyu.edu` | `12345678` |
| `admin2@nyu.edu` | `12345678` |
| `admin3@nyu.edu` | `12345678` |

Any account from `admin1@nyu.edu` through `admin100@nyu.edu` works with password `12345678`. These accounts have pre-seeded Spotify data (genres, artists, match scores) so the full feed, matching, and chat features are available immediately without connecting Spotify.

---

## Deploy Locally

```bash
cp .env.example .env
# fill in .env values — see Discord/Teams for shared secrets
```

**Run everything with Docker:**

Open Docker desktop

```bash
docker-compose up --build
# backend:  http://localhost:8000
# frontend: http://localhost:3000
# mongo:    localhost:27017
```
open http://localhost:3000


**Or run subsystems individually (no Docker):**

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
pip install -r requirements.txt
flask --app app.main run --port 3000
```

**Frontend mock mode** (no backend needed — uses fake data):

```bash
# macOS/Linux
cd frontend && MOCK_MODE=true flask --app app.main run --port 3000

# PowerShell
cd frontend; $env:MOCK_MODE="true"; flask --app app.main run --port 3000
```

---

## Tests

Each subsystem has its own `pyproject.toml` that sets the coverage flags. Run from the subsystem root — no extra flags needed.

```bash
# Backend (runs test_database.py + test_spotify.py, ≥80% target)
cd backend
pytest

# Frontend (runs test_routes.py, ≥80% required)
cd frontend
pytest
```

Test files bootstrap their own env vars via `os.environ.setdefault`, so no `.env` file is required to run tests.

**Current coverage status:**

| Subsystem | Tests | Coverage | CI threshold |
|---|---|---|---|
| Backend | 186 passing | 91% | 80% ✓ |
| Frontend | 78 passing | 83% | 80% ✓ |

