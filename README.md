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

---

## CI/CD Pipeline

Defined in [`.github/workflows/`](.github/workflows/).

**Triggers:**
- `pull_request` → `main`: runs tests only
- `push` → `main` (i.e. PR merged): tests → Docker build+push → Digital Ocean deploy

**Backend pipeline** (`backend.yml`):
1. `pytest --cov=app --cov-fail-under=80`
2. `docker build` → push `vibe-backend:latest` to Docker Hub
3. SSH into DO droplet → `docker pull` + `docker run`

**Frontend pipeline** (`frontend.yml`):
1. `pytest --cov=app --cov-fail-under=80`
2. `docker build` → push `vibe-frontend:latest` to Docker Hub
3. SSH into DO droplet → `docker pull` + `docker run`

**Required GitHub secrets:**

| Secret | Purpose |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub account |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `DO_HOST` | Digital Ocean droplet IP |
| `DO_USER` | SSH user (e.g. `root`) |
| `DO_SSH_KEY` | Private SSH key for the droplet |

---

## Key URLs (local)

| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
