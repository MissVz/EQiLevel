# app/models.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any, List

class EmotionSignals(BaseModel):
    label: Literal["frustrated","engaged","bored","calm"]
    sentiment: float = Field(ge=-1.0, le=1.0)

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
    user_text: str
    session_id: Optional[str] = None
    correct: Optional[bool] = None

class TurnContext(BaseModel):
    transcript: str
    emotion: EmotionSignals
    performance: PerformanceSignals
    mcp: MCP

class TutorReply(BaseModel):
    text: str
    mcp: MCP
    reward: Optional[float] = None
