# PASS/FAIL E2E DB health checker
# Run:  python tests/test_smoke_postgres.py

import os
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

def test_postgres_connection():
    try:
        conn = psycopg2.connect(DB_URL)
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
