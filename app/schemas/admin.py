from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict

class AdminTurn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ts: datetime
    session_id: str
    user_text: str
    reply_text: str
    reward: Optional[float]
    emotion: Dict[str, Any]
    performance: Dict[str, Any]
    mcp: Dict[str, Any]
