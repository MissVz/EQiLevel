# app/models.py
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Literal, Dict, Union, Any

# ---------- Pydantic models ----------
class AdminTurn(BaseModel):
    id: int
    session_id: Union[int, str]
    user_text: str
    reply_text: str
    emotion: Dict[str, Any]
    performance: Dict[str, Any]
    mcp: Dict[str, Any]
    reward: float
    created_at: datetime

    # allow constructing by field name even when alias exists
    model_config = ConfigDict(populate_by_name=True)
    
class EmotionSignals(BaseModel):
    label: Literal["frustrated","engaged","bored","calm"]
    sentiment: float = Field(..., ge=-1.0, le=1.0)

class PerformanceSignals(BaseModel):
    correct: Optional[bool] = None
    attempts: Optional[int] = None
    time_to_solve_sec: Optional[float] = None
    accuracy_pct: Optional[float] = None

class LearningStyle(BaseModel):
    visual: float = 0.0
    auditory: float = 0.0
    reading_writing: float = 0.0
    kinesthetic: float = 0.0

class MCP(BaseModel):
    # state inputs
    emotion: EmotionSignals
    performance: PerformanceSignals
    learning_style: LearningStyle
    # adaptive control
    tone: Literal["warm","encouraging","neutral","concise"]
    pacing: Literal["slow","medium","fast"]
    difficulty: Literal["down","hold","up"]
    style: Literal["visual","auditory","reading_writing","kinesthetic","mixed"]
    next_step: Literal["explain","example","prompt","quiz","review"]
    
class TurnRequest(BaseModel):
    user_text: str = Field(..., example="I keep messing up fractions and feel stuck.")
    session_id: Union[int, str, None] = Field(None, example="61")
    correct: Optional[bool] = None

    @field_validator("session_id", mode="before")
    @classmethod
    def _coerce_session_id(cls, v):
        if v is None or isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v  # leave non-numeric strings to storage.resolve_session_id
    
class TurnContext(BaseModel):
    transcript: str
    emotion: EmotionSignals
    performance: PerformanceSignals
    mcp: MCP

class TutorReply(BaseModel):
    text: str
    mcp: MCP
    reward: Optional[float] = None
