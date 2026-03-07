import time
import logging
from typing import Dict, Any, List
from jarvis_common.schemas import Session

logger = logging.getLogger(__name__)

class SessionGoalTracker:
    """
    Phase 3: Session Goal Tracking
    Infers user goals from command sequences and evaluates success.
    """
    def __init__(self, db=None, inactivity_timeout: float = 60.0):
        self.db = db
        self.inactivity_timeout = inactivity_timeout
        self.active_sessions: Dict[str, Session] = {}

    def handle_command(self, session_id: str, command: str):
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = Session(session_id=session_id)
            
        session = self.active_sessions[session_id]
        session.commands.append(command)
        session.last_activity = time.time()
        
        # Infer goal every 5 commands or if not set yet
        if len(session.commands) % 5 == 0 or session.inferred_goal is None:
            self._infer_goal(session)

    def _infer_goal(self, session: Session):
        """Mock LLM call to infer session goal."""
        commands_str = ", ".join(session.commands[-5:])
        
        # In production, call LLM here.
        # "Given these commands, what is the user's overall goal in one sentence?"
        # Mock logic based on keywords:
        if "fastapi" in commands_str.lower():
            session.inferred_goal = "Build a FastAPI application"
        elif "react" in commands_str.lower() or "npm" in commands_str.lower():
            session.inferred_goal = "Develop a React frontend"
        else:
            session.inferred_goal = f"Execute system commands ({len(session.commands)} steps)"
            
        logger.info(f"Session {session.session_id} inferred goal: {session.inferred_goal}")

    async def check_timeouts(self):
        """Check for inactive sessions and evaluate them."""
        now = time.time()
        completed = []
        for s_id, session in list(self.active_sessions.items()):
            if now - session.last_activity > self.inactivity_timeout:
                await self._evaluate_session_success(session)
                completed.append(s_id)
                
        for s_id in completed:
            del self.active_sessions[s_id]

    async def _evaluate_session_success(self, session: Session):
        """Mock LLM call to determine if goal was achieved."""
        # "Given this goal and the full command sequence, was the goal achieved?"
        session.goal_achieved = True
        session.achievement_confidence = 0.95
        
        logger.info(f"Session {session.session_id} completed. Goal achieved: {session.goal_achieved}")
        
        if self.db:
            try:
                # Assuming db has a save_session method or using raw sqlite
                pass 
            except Exception as e:
                logger.error(f"Failed to save session to DB: {e}")
