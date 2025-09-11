# app/db/schema.py
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase): pass

class Setting(Base):
    __tablename__ = "settings"
    key = sa.Column(sa.String, primary_key=True)
    value = sa.Column(sa.Text, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    name = sa.Column(sa.String, nullable=False, unique=True)
    created_at = sa.Column(sa.TIMESTAMP, server_default=sa.text("now()"), nullable=False)

    # relationships
    sessions = relationship("SessionUser", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    created_at = sa.Column(sa.TIMESTAMP, server_default=sa.text("now()"), nullable=False)
    turns = relationship("Turn", back_populates="session", cascade="all, delete-orphan")

class SessionUser(Base):
    __tablename__ = "session_users"
    session_id = sa.Column(sa.BigInteger, sa.ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    user_id = sa.Column(sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = sa.Column(sa.TIMESTAMP, server_default=sa.text("now()"), nullable=False)

    session = relationship("Session")
    user = relationship("User", back_populates="sessions")

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
