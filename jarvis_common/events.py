from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from enum import Enum
import time

class EventType(str, Enum):
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"
    SYSTEM_LOG = "system_log"
    MUTATION_APPLIED = "mutation_applied"

class JarvisEvent(BaseModel):
    """
    Gap 19: Shared Contract between Jarvis voice agent and Self-Improver
    """
    event_id: str
    event_type: EventType
    source: str = "jarvis_voice"
    timestamp: float = Field(default_factory=time.time)
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
