# PASS/FAIL E2E DB health checker
# Run:  python tests/test_smoke_postgres.py

import os
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

def _normalize_for_psycopg2(url: str) -> str:
    """Allow SQLAlchemy-style URLs by stripping the "+driver" suffix.
    psycopg2.connect() accepts libpq URLs like postgresql://... but not
    postgresql+psycopg2://... .
    """
    if "+psycopg2" in url:
        return url.replace("postgresql+psycopg2", "postgresql").replace("postgres+psycopg2", "postgres")
    if "+psycopg" in url:
        return url.replace("postgresql+psycopg", "postgresql").replace("postgres+psycopg", "postgres")
    return url

def test_postgres_connection():
    try:
        conn = psycopg2.connect(_normalize_for_psycopg2(DB_URL))
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        assert cur.fetchone()[0] == 1
        cur.close()
        conn.close()
        print("Postgres connection: OK")
    except Exception as e:
        print(f"Postgres connection: FAIL ({e})")
        assert False, f"Postgres connection failed: {e}"

if __name__ == "__main__":
    test_postgres_connection()
