# Database Notes (Postgres)

This project logs tutoring turns and session metadata to Postgres. The active ORM schema (SQLAlchemy) is defined in `app/db/schema.py`.

---

## Table of Contents

- [Tables (current)](#tables-current)
- [Connection & health](#connection--health)
- [Minimal local setup](#minimal-local-setup)
- [Extended schema (optional)](#extended-schema-optional)

---

## Tables (current)

- users
  - `id BIGSERIAL PRIMARY KEY`
  - `name TEXT UNIQUE NOT NULL`
  - `created_at TIMESTAMP DEFAULT now()`

- sessions
  - `id BIGSERIAL PRIMARY KEY`
  - `created_at TIMESTAMP DEFAULT now()`

- session_users
  - `session_id BIGINT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE`
  - `user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE`
  - `created_at TIMESTAMP DEFAULT now()`

- turns
  - `id BIGSERIAL PRIMARY KEY`
  - `session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE`
  - `user_text TEXT NOT NULL`
  - `reply_text TEXT NOT NULL`
  - `emotion JSON NOT NULL`
  - `performance JSON NOT NULL` (may include `objective_code`)
  - `mcp JSON NOT NULL`
  - `reward DOUBLE PRECISION NOT NULL`
  - `created_at TIMESTAMP DEFAULT now()`

- settings
  - `key TEXT PRIMARY KEY`
  - `value TEXT NOT NULL`

Recommended index:

```sql
CREATE INDEX IF NOT EXISTS idx_turns_session_created
  ON turns (session_id, created_at DESC);
```

---

## Connection & health

- The API reads `DATABASE_URL` from `.env` (example: `postgresql+psycopg2://eqi:eqipw@localhost:5432/eqilevel`).
- On startup, tables are created automatically if missing.
- A quick health checker is available at `GET /api/v1/health/full` and `tests/test_smoke_postgres.py`.

`tests/test_smoke_postgres.py` accepts SQLAlchemy-style URLs and normalizes to a psycopg2 URL for direct `psycopg2.connect(...)`.

---

## Minimal local setup

```bash
docker run -d --name eqilevel-db \
  -e POSTGRES_USER=eqi -e POSTGRES_PASSWORD=eqipw -e POSTGRES_DB=eqilevel \
  -p 5432:5432 postgres:16

python -m venv .venv
.\.venv\Scripts\Activate.ps1  # PowerShell
pip install -r requirements.txt

# .env
echo OPENAI_API_KEY=sk-...> .env
echo DATABASE_URL=postgresql+psycopg2://eqi:eqipw@localhost:5432/eqilevel>> .env

uvicorn app.main:app --reload --port 8000
```

Verify turns being logged:

```bash
docker exec -it eqilevel-db psql -U eqi -d eqilevel \
  -c 'SELECT id, session_id, reward, created_at FROM "turns" ORDER BY id DESC LIMIT 10;'
```

---

## Extended schema (optional)

The file `app/db/ddl.sql` contains a richer, student-centric schema (students, objectives, events, affect logs, interventions, MCP snapshots) intended for future expansion and reporting. It is not automatically applied by the API. If you want to experiment with it, load it manually in a separate database/schema and adapt the services.

