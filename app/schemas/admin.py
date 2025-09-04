from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict

class AdminTurn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    user_text: str
    reply_text: str
    emotion: dict
    performance: dict
    mcp: dict
    reward: float
    created_at: datetime 
