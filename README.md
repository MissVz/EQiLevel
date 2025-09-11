# EQiLevel — Emotion‑Aware RL Tutoring (Manual MVP & PoC)

> An emotionally adaptive AI tutor that blends Whisper-based speech, sentiment cues, a Model Context Protocol (MCP), GPT-driven dialogue, and an RL policy to adjust tone, pacing, and difficulty in real time.

This README reflects the current **local Manual MVP/PoC** (excluding FlowiseAI and Render cloud pieces) and incorporates our migration to **Postgres** with a guaranteed turn‑logging route, admin views, and metrics endpoints. It supersedes earlier READMEs while preserving their intent and scope.

---

## At a Glance

- 🎙 **Voice-to-Tutor Loop (PoC):** Whisper STT → emotion signals → MCP → GPT tutor reply → log turn.  
- 🧠 **Adaptive Control:** Q-learning baseline + policy helpers operate on MCP state to nudge difficulty/pace/tone.  
- 🗄 **Persistence:** Postgres (Docker) with `sessions` and `turns` tables; BIGINT FK with **ON DELETE CASCADE**; smoke test validates E2E.  
- 🧩 **Modular FastAPI:** Health, admin (typed & raw), session (conversation), debug, and a **guaranteed logger** route to persist a turn deterministically.  
- 🔐 **Local-first:** Single `.env` controls OpenAI and DB; all endpoints are runnable locally for Manual MVP demos.

---

## Repo Structure (key files)

```
EQiLevel/
├─ app/
│  ├─ main.py                       # FastAPI app (lifespan init_db, router includes)
│  ├─ api/v1/
│  │  ├─ health_router.py           # /api/v1/health, /api/v1/health/full
│  │  ├─ admin_router.py            # /api/v1/admin/turns, /api/v1/admin/turns_raw, /api/v1/admin/summary
│  │  ├─ session_router.py          # /session/start (create Session row)
│  │  ├─ metrics_router.py          # /api/v1/metrics, /api/v1/metrics/series
│  │  ├─ emotion_router.py          # /emotion/detect_text, /emotion/detect_audio
│  │  ├─ debug_router.py            # /api/v1/debug/db
│  │  └─ turn_logger_router.py      # /api/v1/turn/log (guaranteed persistence)
│  ├─ services/
│  │  ├─ mcp.py, policy.py, tutor.py, emotion.py, reward.py, metrics.py, admin_summary.py, security.py
│  │  └─ storage.py                 # SQLAlchemy engine (DATABASE_URL), SessionLocal, init_db, queries
│  ├─ db/
│  │  └─ schema.py                  # ORM: Session(id, created_at), Turn(session_id,…)
│  └─ schemas/
│     └─ admin.py / models.py       # Pydantic models (e.g., AdminTurn, TurnRequest)
├─ samples/mcp_sample.json          # Minimal payload for /session and /turn/log
├─ tests/test_smoke_postgres.py        # PASS/FAIL E2E DB health checker
├─ requirements.txt                 # SQLAlchemy 2.x, Postgres driver, FastAPI, Uvicorn, dotenv, requests
└─ .env                             # OPENAI_API_KEY, DATABASE_URL
```

---

## Data Model

**sessions**  
- `id BIGINT PRIMARY KEY`  
- `created_at TIMESTAMP DEFAULT now()`  

**turns**  
- `id BIGINT PRIMARY KEY`  
- `session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE`  
- `user_text VARCHAR NOT NULL` / `reply_text VARCHAR NOT NULL`  
- `emotion JSON NOT NULL` / `performance JSON NOT NULL` / `mcp JSON NOT NULL`  
- `reward DOUBLE PRECISION NOT NULL`  
- `created_at TIMESTAMP DEFAULT now()`  

> Optional index:
>
> ```sql
> CREATE INDEX IF NOT EXISTS idx_turns_session_created
>   ON turns (session_id, created_at DESC);
> ```

---

## Setup

### 1) Postgres (Docker)

```bash
docker run -d --name eqilevel-db   -e POSTGRES_USER=eqi -e POSTGRES_PASSWORD=eqipw -e POSTGRES_DB=eqilevel   -p 5432:5432 postgres:16
```

### 2) Python env + deps

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Windows cmd.exe: .\.venv\Scripts\activate
pip install -r requirements.txt
```

Driver note (psycopg2 vs psycopg v3):
- The default `requirements.txt` uses `psycopg2`, so the URL scheme should be `postgresql+psycopg2://...`.
- If you prefer psycopg v3, install `psycopg[binary]` and use `postgresql+psycopg://...`.

### 3) Environment

Create `.env` at repo root:

```ini
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg2://eqi:eqipw@localhost:5432/eqilevel
```

### 4) Run API

```bash
uvicorn app.main:app --reload --port 8000
```

Startup prints that `DATABASE_URL` and `OPENAI_API_KEY` are loaded; DB tables are created on first run.

---

## Endpoints

### Health
- `GET /api/v1/health` (liveness)  
- `GET /api/v1/health/full` (OpenAI key presence + DB + ffmpeg on PATH)  

### Conversation (Manual MVP)
- `POST /session`  
  Accepts either JSON (`{ user_text, session_id? }`) or `multipart/form-data` with `file` (audio) and optional `session_id`. If audio is provided, it is transcribed via Whisper before tutoring. Returns tutor `text`, updated `mcp`, and `reward`.  
  > `session_id` may be string or int (coerced to BIGINT in storage).  
- `POST /session/start`  
  Returns a new numeric `session_id` (convenience helper for clients).

### Voice/WebSocket
- `WS /ws/voice`  
  Streams small audio chunks, returns partial transcripts and, on stop, the final transcript and a tutor reply using the same pipeline as `/session`.

### Guaranteed Logger (PoC persistence)
- `POST /api/v1/turn/log?reward=0.05`  
  Body:
  ```json
  { "session_id": 1, "user_text": "…", "reply_text": "…", "emotion": {}, "performance": {}, "mcp": {} }
  ```
  Returns: `{ "ok": true, "turn_id": … }`. Fails with 400 if session does not exist.

### Admin
- `GET /api/v1/admin/turns_raw?limit=10` → raw DB rows (debug-friendly)
- `GET /api/v1/admin/turns?limit=10`     → typed model (`session_id:int`, `created_at:datetime`)
- `GET /api/v1/admin/summary`            → per-session totals and last-turn snapshot

### Debug
- `GET /api/v1/debug/db` → current DB URL (masked) + counts  

### Metrics
- `GET /api/v1/metrics` → metrics snapshot (optionally filtered by `session_id`, `since_minutes`/`hours`)
- `GET /api/v1/metrics/series` → time-series for charts (bucket=`minute|hour`)
- Also available (legacy): `GET /metrics` at the app root.

### Emotion
- `POST /emotion/detect_text` → simple text-based emotion classification
- `POST /emotion/detect_audio` → audio-based emotion classification (SpeechBrain)

---

## Admin Auth

Some admin endpoints require an API key header. Set the key in your API environment and the UI Settings page:

- API: add to `.env`  
  `ADMIN_API_KEY=your-secret-key`
- UI: Settings → “Admin Key (X-Admin-Key)” (or build with `VITE_ADMIN_KEY`). The UI will send this in `X-Admin-Key`.

---

## Streaming Settings

WebSocket streaming has server-side failsafes. You can tune these via environment variables:

- `STREAM_MAX_SECONDS` (default `25`) — maximum time a single stream can run before auto-finalization.  
- `STREAM_STALE_PARTIAL_SECONDS` (default `10`) — finalize if no new partial transcript has been produced for this many seconds while audio exists.  

The UI Settings page also exposes VAD controls that affect client‑side auto-stop:

- Silence threshold (RMS): increase in noisy rooms (e.g., `0.04–0.06`).  
- Silence duration to stop (ms): shorten to finalize faster (e.g., `900–1500`).

---

## Quickstart: Minimal E2E

```bash
# 1) create a session
docker exec -it eqilevel-db psql -U eqi -d eqilevel   -c "INSERT INTO sessions DEFAULT VALUES RETURNING id;"

# 2) log a turn (guaranteed)
curl -X POST "http://127.0.0.1:8000/api/v1/turn/log?reward=0.05"   -H "Content-Type: application/json"   --data-binary @samples/mcp_sample.json

# 3) verify
docker exec -it eqilevel-db psql -U eqi -d eqilevel   -c 'SELECT id, session_id, user_text, reward FROM "turns" ORDER BY id DESC LIMIT 5;'
```

Or run the smoke test (does all of the above with PASS/FAIL):

```bash
python tests/test_smoke_postgres.py
# Output should end with: Overall: PASS ✅
```

---

## MCP, Emotion, and Policy (overview)

- **MCP** encodes the learner and interaction state (affect, pace/tone/difficulty, strategy hints) for the tutor and policy to read/write. Using MCP makes adaptation **interpretable** and unit‑testable.  
- **Emotion**: lightweight signals (e.g., calm/frustrated + sentiment score) are extracted and logged; the reward function can incorporate affect trends (Manual MVP).  
- **Policy**: a Q‑learning baseline supports small, transparent adjustments (pace/difficulty/tone), with room to plug in deeper RL later.

---

## Roadmap (next local milestones)

- Small dashboards for the metrics router; unify docs and UI.
- Enrich turn schema with task/objective tags to enable mastery/progress views.
- JSONB migration + GIN indexes for structured queries on emotion/performance/MCP.
- Unit/integration tests for routers and storage (pytest).
- (Beyond Manual MVP) reconnect Flowise orchestration and cloud deploys.

---

## Acknowledgements

- **OpenAI assistance**:  
  OpenAI. (2025). *ChatGPT’s assistance [Large language model]. https://openai.com/chatgpt

- This independent project is part of **AI687 AI Capstone** at City University of Seattle.

---

## License

MIT (project code).
### One‑click Demo (Windows)

```powershell
./scripts/demo_start.ps1 -Port 8000
```

This builds the SPA (Vite), copies `ui/dist` to `app/web`, and starts FastAPI on the specified port. Ensure `ffmpeg` is on your PATH for webm/opus transcription.
