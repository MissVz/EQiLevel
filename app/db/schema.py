# app/db/schema.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, JSON, ForeignKey, DateTime, func

class Base(DeclarativeBase): pass

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    turns: Mapped[list["Turn"]] = relationship(back_populates="session")

class Turn(Base):
    __tablename__ = "turns"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    user_text: Mapped[str] = mapped_column(String)
    reply_text: Mapped[str] = mapped_column(String)
    emotion: Mapped[dict] = mapped_column(JSON)
    performance: Mapped[dict] = mapped_column(JSON)
    mcp: Mapped[dict] = mapped_column(JSON)
    reward: Mapped[float] = mapped_column(Float)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[Session] = relationship(back_populates="turns")
