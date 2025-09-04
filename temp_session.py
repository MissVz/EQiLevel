from sqlalchemy import text
from app.services.storage import engine

with engine.begin() as c:
    sid = c.execute(text("INSERT INTO sessions DEFAULT VALUES RETURNING id")).scalar()
    print(sid)
