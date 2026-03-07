"""
Self-Critique Engine for Jarvis-OS
Uses Cloud LLM (Gemini) to perform genuine reasoning on session logs and exceptions,
generating verified Mutation directives instead of relying on regex heuristics.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Try loading GEMINI_API_KEY
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "DUMMY_KEY"))

class AnalyzedError(BaseModel):
    error_type: str = Field(description="The canonical class of the exception (e.g. MemoryError, Timeout)")
    root_cause: str = Field(description="A 1-sentence explanation of what really triggered the error.")
    suggested_mutation: str = Field(description="Specific config or code adjustment to fix this logic.")
    confidence: float = Field(description="0.0 to 1.0 confidence score that this mutation resolves the error.")

class SelfCritiqueEngine:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model = genai.GenerativeModel(model_name)
    
    def critique_session(self, logs: List[Dict[str, Any]]) -> List[AnalyzedError]:
        """
        Passes a batch of JSON session logs to the LLM to identify why 
        failures are happening and produce intelligent mutations.
        """
        if not logs:
            return []
            
        prompt = f"""
        You are the Jarvis-OS Self-Critique Engine. You review system execution logs.
        Find the root cause of 'ERROR' level logs. Do not just parse the syntax, find the 
        logical problem (e.g., 'file is locked by another process' or 'Regex Router hallucinated').
        Output MUST be pure JSON matching this array structure:
        [
          {{
            "error_type": "string",
            "root_cause": "string",
            "suggested_mutation": "string",
            "confidence": 0.95
          }}
        ]
        
        Logs:
        {json.dumps(logs, indent=2)}
        """
        
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()
            # Clean up markdown
            if raw_text.startswith("```json"):
                raw_text = raw_text.strip("```json").strip("```").strip()
                
            data = json.loads(raw_text)
            return [AnalyzedError(**item) for item in data]
        except Exception as e:
            logger.error(f"Failed to generate self-critique: {e}")
            return []
