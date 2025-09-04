# app/db/schema.py
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase): pass

class Session(Base):
    __tablename__ = "sessions"
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(sa.TIMESTAMP, server_default=sa.text("now()"), nullable=False)
    turns = relationship("Turn", back_populates="session", cascade="all, delete-orphan")

class Turn(Base):
    __tablename__ = "turns"
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)

    session_id = sa.Column(sa.BigInteger, sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    user_text   = sa.Column(sa.String, nullable=False)
    reply_text  = sa.Column(sa.String, nullable=False)
    emotion     = sa.Column(sa.JSON,   nullable=False)
    performance = sa.Column(sa.JSON,   nullable=False)
    mcp         = sa.Column(sa.JSON,   nullable=False)
    reward      = sa.Column(sa.Float,  nullable=False)
    created_at  = sa.Column(sa.TIMESTAMP, server_default=sa.text("now()"), nullable=False)

    session = relationship("Session", back_populates="turns")
