# EQiLevel - Emotion-Aware RL Tutoring (Manual MVP & PoC)

An emotionally adaptive AI tutor that blends Whisper-based speech, lightweight emotion cues, a Model Context Protocol (MCP), GPT-driven dialogue, and a Q-learning policy to adjust tone, pacing, and difficulty in real time.

This README reflects the current local Manual MVP/PoC and the migration to Postgres with a guaranteed turn-logging route, admin views, and metrics endpoints.

---

## Table of Contents

- [At a Glance](#at-a-glance)
- [Repo Layout (key files)](#repo-layout-key-files)
- [Data Model](#data-model)
- [Setup](#setup)
- [Endpoints](#endpoints)
- [Admin Auth](#admin-auth)
- [Streaming Settings](#streaming-settings)
- [Quickstart: Minimal E2E](#quickstart-minimal-e2e)
- [UI (optional)](#ui-optional)
- [Acknowledgements](#acknowledgements)
- [License](#license)
- [One-click Demo (Windows)](#one-click-demo-windows)

---

## At a Glance

- Voice-to-tutor loop: Whisper STT + emotion signals + MCP + GPT reply + persist turn
- Adaptive control: Q-learning baseline nudges difficulty/pace/tone
- Persistence: Postgres (Docker) with sessions/turns; E2E smoke test
- Modular FastAPI: health, admin, session, metrics, emotion, users, objectives, settings, turn logger
- Local-first: single `.env` drives OpenAI + DB config

---

## Repo Layout (key files)

```
EQiLevel/
  app/
    main.py                     # FastAPI app (lifespan init_db, router includes)
    api/v1/
      health_router.py          # /api/v1/health, /api/v1/health/full
      admin_router.py           # /api/v1/admin/turns, /turns_raw, /summary
      session_router.py         # /session/start (create session & optional user)
      metrics_router.py         # /api/v1/metrics, /api/v1/metrics/series
      emotion_router.py         # /emotion/detect_text, /emotion/detect_audio
      debug_router.py           # /api/v1/debug/db
      turn_logger_router.py     # /api/v1/turn/log (guaranteed persistence)
      users_router.py           # /api/v1/users (list/create), /by_session
      objectives_router.py      # /api/v1/objectives, /{code}, /progress
      settings_router.py        # /api/v1/settings/system_prompt (get/set)
    services/
      mcp.py, policy.py, tutor.py, emotion.py, reward.py, metrics.py, admin_summary.py, security.py, storage.py
    db/schema.py                # ORM: Users, Session, SessionUser, Turn, Setting
    schemas/admin.py            # Pydantic admin view models
  ui/                           # Vite + React SPA (optional)
  samples/mcp_sample.json       # Minimal payload for /turn/log
  tests/test_smoke_postgres.py  # PASS/FAIL Postgres health checker
  requirements.txt              # FastAPI, SQLAlchemy, psycopg2, Torch, etc.
  .env                          # OPENAI_API_KEY, DATABASE_URL, ADMIN_API_KEY
```

---

## Data Model

- sessions: id BIGSERIAL PK, created_at TIMESTAMP DEFAULT now()
- turns: id BIGSERIAL PK; session_id BIGINT FK (ON DELETE CASCADE); user_text, reply_text, emotion JSON, performance JSON, mcp JSON, reward FLOAT, created_at TIMESTAMP
- users: id BIGSERIAL PK; name UNIQUE; created_at TIMESTAMP
- session_users: session_id BIGINT PK, user_id BIGINT; binds session to a user
- settings: key TEXT PK, value TEXT

Optional index:

```sql
CREATE INDEX IF NOT EXISTS idx_turns_session_created
  ON turns (session_id, created_at DESC);
```

---

## Setup

1) Postgres (Docker)

```bash
docker run -d --name eqilevel-db \
  -e POSTGRES_USER=eqi -e POSTGRES_PASSWORD=eqipw -e POSTGRES_DB=eqilevel \
  -p 5432:5432 postgres:16
```

2) Python env + deps

```bash
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
# cmd.exe: .\.venv\Scripts\activate
pip install -r requirements.txt
```

Driver note: requirements use `psycopg2`, so prefer `postgresql+psycopg2://...` for `DATABASE_URL`.

3) Environment

Create `.env` at repo root:

```ini
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg2://eqi:eqipw@localhost:5432/eqilevel
ADMIN_API_KEY=your-secret-key
```

4) Run API

```bash
uvicorn app.main:app --reload --port 8000
```

Startup prints that variables are loaded; DB tables are created on first run.

---

## Endpoints

Health
- GET `/api/v1/health` (liveness)
- GET `/api/v1/health/full` (OpenAI key, DB, ffmpeg checks)

Conversation
- POST `/session` - JSON `{ user_text, session_id?, chat_history_turns? }` or `multipart/form-data` with `file` (audio) and optional `session_id` and `objective_code`. If audio is provided, it is transcribed via Whisper then processed. Returns tutor `text`, updated `mcp`, and `reward`.
- POST `/session/start` - returns `{ session_id }`. Optional body `{ user_name?, user_id? }` binds a user to the session for admin/progress views.

WebSocket (voice)
- WS `/ws/voice` - streams audio chunks and emits partial transcripts. On stop, returns the final transcript and a tutor reply using the same pipeline as `/session`.
  Required query params: `session_id`, `objective_code`. The session must be bound to a user (start the session with `user_name` or bind via users endpoints).

Guaranteed Logger
- POST `/api/v1/turn/log?reward=0.05` - body:

```json
{ "session_id": 1, "user_text": "...", "reply_text": "...", "emotion": {}, "performance": {}, "mcp": {} }
```

Returns `{ ok: true, turn_id }`. Fails with 400 if the session does not exist.

Admin
- GET `/api/v1/admin/turns_raw?limit=10` - raw DB rows (debug-friendly)
- GET `/api/v1/admin/turns?limit=10` - typed model view
- GET `/api/v1/admin/summary` - per-session totals and last-turn snapshot

Debug
- GET `/api/v1/debug/db` - masked DB URL + counts

Metrics
- GET `/api/v1/metrics` - snapshot (optionally filter by `session_id`, `since_minutes|since_hours`)
- GET `/api/v1/metrics/series` - time series for charts (`bucket=minute|hour`)

Emotion
- POST `/emotion/detect_text`
- POST `/emotion/detect_audio`

Users
- GET `/api/v1/users?q=al&limit=20` - list
- POST `/api/v1/users` body `{ "name": "Alice" }` - create or get
- GET `/api/v1/users/by_session?session_id=123` - resolve bound user

Objectives
- GET `/api/v1/objectives?unit=B&q=fractions` - list
- GET `/api/v1/objectives/{code}` - details
- GET `/api/v1/objectives/progress?session_id=123` - accuracy/reward per objective (uses `performance.objective_code` when present)

Settings (admin)
- GET `/api/v1/settings/system_prompt`
- POST `/api/v1/settings/system_prompt` body `{ "value": "..." }`

---

## Admin Auth

Protected admin routes require `X-Admin-Key: <ADMIN_API_KEY>`. Set `ADMIN_API_KEY` in `.env` and in the UI Settings page (or build with `VITE_ADMIN_KEY`).

---

## Streaming Settings

Server-side failsafes are configurable via env vars:
- `STREAM_MAX_SECONDS` (default 25) - max duration before auto-finalize
- `STREAM_STALE_PARTIAL_SECONDS` (default 10) - finalize if partials stall

The UI exposes VAD controls that affect client-side auto-stop (silence threshold/duration).

---

## Quickstart: Minimal E2E

```bash
# 1) Create a session bound to a user
curl -s -X POST http://127.0.0.1:8000/session/start \
  -H "Content-Type: application/json" \
  -d '{"user_name":"Alice"}'

# 2) Log a turn (guaranteed route)
curl -s -X POST "http://127.0.0.1:8000/api/v1/turn/log?reward=0.05" \
  -H "Content-Type: application/json" \
  --data-binary @samples/mcp_sample.json

# 3) Verify in Postgres
docker exec -it eqilevel-db psql -U eqi -d eqilevel \
  -c 'SELECT id, session_id, user_text, reward FROM "turns" ORDER BY id DESC LIMIT 5;'

# (Optional) Smoke test
python tests/test_smoke_postgres.py
```

---

## UI (optional)

- Dev server: from `ui/` run `npm install && npm run dev` (http://localhost:5173). Set `VITE_API_BASE` or use Settings in the UI.
- Production: `npm run build` creates `ui/dist`. Copy to `app/web` (e.g., `robocopy ui\dist app\web /E` on Windows). FastAPI will serve at `/web` and redirect `/` there.

---

## Acknowledgements

- OpenAI assistance: OpenAI (2025). ChatGPT assistance. https://openai.com/chatgpt
- Project for AI687 AI Capstone at City University of Seattle.

---

## License

MIT

---

## One-click Demo (Windows)

```powershell
./scripts/demo_start.ps1 -Port 8000
```

This builds the SPA (Vite), copies `ui/dist` to `app/web`, and starts FastAPI on the specified port. Ensure `ffmpeg` is on your PATH for webm/opus transcription.

