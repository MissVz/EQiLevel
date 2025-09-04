# EQiLevel — Emotion‑Aware RL Tutoring (Manual MVP & PoC)

> An emotionally adaptive AI tutor that blends Whisper-based speech, sentiment cues, a Model Context Protocol (MCP), GPT-driven dialogue, and an RL policy to adjust tone, pacing, and difficulty in real time.

This README reflects the current **local Manual MVP/PoC** (excluding FlowiseAI and Render cloud pieces) and incorporates our recent migration from SQLite to **Postgres** with a guaranteed turn‑logging route and admin views. It supersedes earlier READMEs while preserving their intent and scope.

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
│  │  ├─ admin_router.py            # /api/v1/admin/turns, /api/v1/admin/turns_raw
│  │  ├─ session_router.py          # /session (conversation loop → tutor reply & log)
│  │  ├─ debug_router.py            # /api/v1/debug/db, /api/v1/debug/events/recent
│  │  └─ turn_logger_router.py      # /api/v1/turn/log (guaranteed persistence)
│  ├─ services/
│  │  ├─ mcp.py, policy.py, tutor.py, emotion.py, reward.py
│  │  └─ storage.py                 # SQLAlchemy engine (DATABASE_URL), SessionLocal, init_db, queries
│  ├─ db/
│  │  └─ schema.py                  # ORM: Session(id, created_at), Turn(session_id,…)
│  └─ schemas/
│     └─ admin.py / models.py       # Pydantic models (e.g., AdminTurn, TurnRequest)
├─ samples/mcp_sample.json          # Minimal payload for /session and /turn/log
├─ scripts/smoke_postgres.py        # PASS/FAIL E2E DB health checker
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
.\.venv\Scriptsctivate
pip install -r requirements.txt
```

If you prefer psycopg v3 on Windows:
- `pip install "psycopg[binary]"`
- set `DATABASE_URL=postgresql+psycopg://eqi:eqipw@localhost:5432/eqilevel` in `.env`

### 3) Environment

Create `.env` at repo root:

```ini
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://eqi:eqipw@localhost:5432/eqilevel
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
- `GET /api/v1/health/full` (OpenAI key presence + DB)  

### Conversation (Manual MVP)
- `POST /session?correct={true|false}&item_id=item_42`  
  Body: `samples/mcp_sample.json` (includes `session_id`, emotion/perf, MCP fields)  
  Returns: tutor `text`, updated `mcp`, and `reward`.  
  > Request model accepts `session_id` as string or int (coerced to BIGINT in storage).

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

### Debug
- `GET /api/v1/debug/db` → current DB/user + counts  
- `GET /api/v1/debug/events/recent?limit=5` → last N turns

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
python scripts/smoke_postgres.py
# Output should end with: Overall: PASS ✅
```

---

## MCP, Emotion, and Policy (overview)

- **MCP** encodes the learner and interaction state (affect, pace/tone/difficulty, strategy hints) for the tutor and policy to read/write. Using MCP makes adaptation **interpretable** and unit‑testable.  
- **Emotion**: lightweight signals (e.g., calm/frustrated + sentiment score) are extracted and logged; the reward function can incorporate affect trends (Manual MVP).  
- **Policy**: a Q‑learning baseline supports small, transparent adjustments (pace/difficulty/tone), with room to plug in deeper RL later.

---

## Roadmap (next local milestones)

- Metrics router + small dashboards (move `/metrics` out of app root; add per‑session summaries).
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
