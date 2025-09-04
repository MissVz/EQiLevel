"""
EQiLevel Postgres Smoke Test
Run:  python scripts/smoke_postgres.py
Requires: DATABASE_URL env, API running on localhost:8000
"""
import os, json, time
import requests
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()  # loads .env from your repo root

API = "http://127.0.0.1:8000"
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL, future=True)

def ok(name, cond):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return cond

def main():
    all_pass = True

    # 1) DB identity
    with engine.connect() as c:
        db, usr = c.execute(text("select current_database(), current_user")).one()
        all_pass &= ok("DB identity", db == "eqilevel" and bool(usr))

    # 2) Schema sanity
    with engine.connect() as c:
        turns_cols = dict(c.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='turns'
        """)).all())
        sessions_cols = dict(c.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name='sessions'
        """)).all())
    all_pass &= ok("Schema: sessions.id bigint", sessions_cols.get("id","").startswith("bigint"))
    all_pass &= ok("Schema: turns.session_id bigint", turns_cols.get("session_id","").startswith("bigint"))

    # 3) Create a session
    with engine.begin() as c:
        new_id = c.execute(text("INSERT INTO sessions DEFAULT VALUES RETURNING id")).scalar()
    all_pass &= ok("Created session", isinstance(new_id, int))

    # 4) Logger route persists
    body = {
        "session_id": new_id,
        "user_text": "smoke turn",
        "reply_text": "ok",
        "emotion": {}, "performance": {}, "mcp": {}
    }
    r = requests.post(f"{API}/api/v1/turn/log?reward=0.01", json=body, timeout=10)
    all_pass &= ok("Logger route 200", r.ok and r.json().get("ok") is True)

    # 5) Row exists
    with engine.connect() as c:
        found = c.execute(text("SELECT count(*) FROM turns WHERE session_id=:sid"), {"sid": new_id}).scalar()
    all_pass &= ok("Turn landed", found >= 1)

    # 6) Cascade delete
    with engine.begin() as c:
        c.execute(text("DELETE FROM sessions WHERE id=:sid"), {"sid": new_id})
    with engine.connect() as c:
        post = c.execute(text("SELECT count(*) FROM turns WHERE session_id=:sid"), {"sid": new_id}).scalar()
    all_pass &= ok("Cascade removed child turns", post == 0)

    # 7) Admin endpoints
    r_raw = requests.get(f"{API}/api/v1/admin/turns_raw?limit=5", timeout=10)
    r_typed = requests.get(f"{API}/api/v1/admin/turns?limit=5", timeout=10)
    all_pass &= ok("Admin raw 200", r_raw.ok)
    all_pass &= ok("Admin typed 200", r_typed.ok)

    print("\nOverall:", "PASS ✅" if all_pass else "FAIL ❌")

if __name__ == "__main__":
    assert DB_URL, "DATABASE_URL must be set"
    main()
