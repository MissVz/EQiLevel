"""
Smoke test for EQiLevel stack:
- Ensures PYTHONPATH includes project root
- Confirms absolute imports (e.g., app.services.metrics) resolve
- Verifies DB connectivity and schema
Run:  python scripts/smoke_postgres.py
Requires: DATABASE_URL env, API running on localhost:8000
"""
import os, sys, importlib.util, json, time
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)  # <-- load .env early
import requests
from app.services.storage import SessionLocal, init_db
from app.db import schema
from sqlalchemy import create_engine, text, inspect


API = "http://127.0.0.1:8000"
DB_URL = os.getenv("DATABASE_URL")
engine = create_engine(DB_URL, future=True)

def ok(name, cond):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return cond

def check_pythonpath():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys_path_has_root = root in sys.path
    env_has_root = os.environ.get("PYTHONPATH", "").find(root) != -1
    if sys_path_has_root or env_has_root:
        print("[PASS] PYTHONPATH includes repo root")
    else:
        print("[FAIL] PYTHONPATH missing repo root:", root)
        raise SystemExit(1)

def check_imports():
    try:
        # Try importing one of your absolute paths
        from app.services.metrics import compute_metrics
        from app.api.v1.metrics_router import get_metrics
        print("[PASS] Absolute imports resolved (app.*)")
    except Exception as e:
        print("[FAIL] Absolute imports failed:", e)
        raise SystemExit(1)

def check_db_schema():
    try:
        init_db()
        with SessionLocal() as db:
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            assert "sessions" in tables, "sessions table missing"
            assert "turns" in tables, "turns table missing"
        print("[PASS] DB schema verified: sessions & turns present")
    except Exception as e:
        print("[FAIL] DB schema check failed:", e)
        raise SystemExit(1)
    
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
    check_pythonpath()
    check_imports()
    check_db_schema()
    main()
