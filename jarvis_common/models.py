"""
Jarvis Common Models
Shared Pydantic structures allowing Jarvis and external agents (like Swara)
to communicate using a uniform schema over IPC / Database layers.
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import time

class SessionEvent(BaseModel):
    """
    Standard event model for all cross-process messaging and Swara integration.
    """
    event_id: str = Field(description="Unique ID for this event")
    project_id: str = Field(default="jarvis-core", description="Identifier of the system generating this event")
    source: str = Field(description="Source component (e.g. Swara-Dev-Agent, Jarvis-Router)")
    event_type: str = Field(description="Categorical type of the event (e.g., 'command_result', 'voice_input')")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary JSON data for the event")
    timestamp: float = Field(default_factory=time.time, description="Unix timestamp of when the event occurred")
    status: Optional[str] = Field(default=None, description="Status code (e.g. 'success', 'failure')")
    error: Optional[str] = Field(default=None, description="Error message if status is 'failure'")
