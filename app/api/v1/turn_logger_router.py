# app/api/v1/turn_logger_router.py
from typing import Optional, Union
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session as SASession
from app.services.storage import SessionLocal
from app.db.schema import Session as DBSession, Turn

router = APIRouter(prefix="/api/v1", tags=["turns"])

# Pydantic body that matches your `turns` table
class TurnLogBody(BaseModel):
    session_id: Union[int, str]
    user_text: str
    reply_text: Optional[str] = None
    emotion: dict
    performance: dict
    mcp: dict

    # Coerce session_id to int so it fits BIGINT FK
    @field_validator("session_id", mode="before")
    @classmethod
    def _coerce_session_id(cls, v):
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ValueError("session_id must be int or numeric string")
        if i <= 0:
            raise ValueError("session_id must be a positive integer")
        return i

class TurnLogResponse(BaseModel):
    ok: bool
    turn_id: int

@router.post("/turn/log", summary="Persist a turn (guaranteed)", response_model=TurnLogResponse)
def log_turn(body: TurnLogBody, reward: float = Query(0.0)):
    with SessionLocal() as db:  # type: SASession
        try:
            sess = db.get(DBSession, body.session_id)
            if not sess:
                raise HTTPException(status_code=400, detail=f"Session {body.session_id} does not exist")

            reply = (body.reply_text or "").strip() or "[no_reply]"
            turn = Turn(
                session_id=body.session_id,
                user_text=body.user_text,
                reply_text=reply,
                emotion=body.emotion,
                performance=body.performance,
                mcp=body.mcp,
                reward=reward,
            )
            db.add(turn)
            db.commit()
            db.refresh(turn)
            return {"ok": True, "turn_id": turn.id}
        except:
            db.rollback()
            raise
    return TurnLogResponse(ok=True, turn_id=turn.id)
