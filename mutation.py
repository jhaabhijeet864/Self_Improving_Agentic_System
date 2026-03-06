"""
Mutation - Self-improvement instruction generator
Automatically updates agent instructions based on feedback and analysis
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class InstructionUpdate:
    """An instruction update recommendation"""
    id: str
    timestamp: float
    category: str  # e.g., "error_handling", "performance", "routing"
    priority: str  # "low", "medium", "high", "critical"
    description: str
    old_instruction: Optional[Dict[str, Any]]
    new_instruction: Dict[str, Any]
    reasoning: str
    confidence_score: float  # 0.0 to 1.0
    applied: bool = False
    result: Optional[Dict[str, Any]] = None


class Mutation:
    """
    Mutation system for self-improvement
    Generates and applies instruction updates based on performance analysis
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize Mutation system
        
        Args:
            max_history: Maximum update history to keep
        """
        self.max_history = max_history
        self.instructions: Dict[str, Any] = {}
        self.update_history: List[InstructionUpdate] = []
        self.performance_baseline: Dict[str, float] = {}
        
    def set_base_instructions(self, instructions: Dict[str, Any]):
        """Set the base agent instructions"""
        self.instructions = instructions.copy()
        logger.info(f"Base instructions set with {len(instructions)} items")
    
    def get_current_instructions(self) -> Dict[str, Any]:
        """Get current active instructions"""
        return self.instructions.copy()
    
    def generate_update(
        self,
        category: str,
        priority: str,
        description: str,
        new_instruction: Dict[str, Any],
        reasoning: str,
        confidence_score: float = 0.8,
        old_instruction: Optional[Dict[str, Any]] = None,
    ) -> InstructionUpdate:
        """
        Generate an instruction update
        
        Args:
            category: Update category
            priority: Priority level
            description: Human-readable description
            new_instruction: New instruction to apply
            reasoning: Reason for the update
            confidence_score: Confidence in the update (0-1)
            old_instruction: Previous instruction being replaced
            
        Returns:
            InstructionUpdate object
        """
        import time
        import uuid
        
        update = InstructionUpdate(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            category=category,
            priority=priority,
            description=description,
            old_instruction=old_instruction,
            new_instruction=new_instruction,
            reasoning=reasoning,
            confidence_score=min(1.0, max(0.0, confidence_score)),
        )
        
        self.update_history.append(update)
        
        # Keep history size bounded
        if len(self.update_history) > self.max_history:
            self.update_history = self.update_history[-self.max_history:]
        
        logger.info(
            f"Generated update: {category} ({priority}) - {description}"
        )
        
        return update
    
    def apply_update(self, update: InstructionUpdate) -> bool:
        """
        Apply an instruction update
        
        Args:
            update: InstructionUpdate to apply
            
        Returns:
            True if applied successfully
        """
        try:
            # Store old instruction
            if "name" in update.new_instruction:
                name = update.new_instruction["name"]
                update.old_instruction = self.instructions.get(name)
                self.instructions[name] = update.new_instruction
            else:
                # If no name, treat as a category update
                category = update.category
                if category not in self.instructions:
                    self.instructions[category] = {}
                self.instructions[category].update(update.new_instruction)
            
            update.applied = True
            update.result = {
                "status": "success",
                "applied_at": datetime.now().isoformat(),
            }
            
            logger.info(f"Applied update: {update.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply update {update.id}: {e}")
            update.result = {
                "status": "failed",
                "error": str(e),
            }
            return False
    
    def apply_multiple_updates(self, updates: List[InstructionUpdate]) -> Dict[str, bool]:
        """Apply multiple updates, prioritizing by confidence and priority"""
        
        # Sort by priority and confidence
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        sorted_updates = sorted(
            updates,
            key=lambda x: (
                priority_order.get(x.priority, 0),
                x.confidence_score,
            ),
            reverse=True,
        )
        
        results = {}
        for update in sorted_updates:
            results[update.id] = self.apply_update(update)
        
        return results
    
    def generate_suggestions(
        self,
        analysis_result: Dict[str, Any],
    ) -> List[InstructionUpdate]:
        """
        Generate instruction updates based on analysis results
        
        Args:
            analysis_result: Result from Autopsy analysis
            
        Returns:
            List of suggested InstructionUpdate objects
        """
        suggestions = []
        
        # Extract metrics
        error_rate = analysis_result.get("error_rate", 0.0)
        avg_time = analysis_result.get("avg_execution_time", 0.0)
        patterns = analysis_result.get("patterns", [])
        hotspots = analysis_result.get("hotspots", [])
        
        # Generate error handling updates
        if error_rate > 0.1:
            suggestions.append(
                self.generate_update(
                    category="error_handling",
                    priority="high" if error_rate > 0.2 else "medium",
                    description=f"High error rate detected ({error_rate*100:.1f}%)",
                    new_instruction={
                        "name": "error_handling",
                        "retry_strategy": "exponential_backoff",
                        "max_retries": 3,
                        "retry_delay": 1.0,
                    },
                    reasoning=f"Error rate of {error_rate*100:.1f}% suggests need for better error recovery",
                    confidence_score=0.85,
                )
            )
        
        # Generate performance optimizations
        if avg_time > 5.0:
            suggestions.append(
                self.generate_update(
                    category="performance",
                    priority="medium",
                    description=f"Slow execution detected (avg {avg_time:.2f}s)",
                    new_instruction={
                        "name": "executor_config",
                        "max_workers": 15,
                        "timeout": 300.0,
                        "batch_mode": True,
                    },
                    reasoning=f"Average execution time of {avg_time:.2f}s indicates need for parallelization",
                    confidence_score=0.75,
                )
            )
        
        # Generate routing updates based on patterns
        if hotspots:
            top_hotspot = hotspots[0]
            suggestions.append(
                self.generate_update(
                    category="routing",
                    priority="low",
                    description=f"Optimize routing for {top_hotspot['task_id']}",
                    new_instruction={
                        "name": "routing_rules",
                        "priority_tasks": [top_hotspot["task_id"]],
                        "use_caching": True,
                    },
                    reasoning="Performance hotspot identified - route more efficiently",
                    confidence_score=0.7,
                )
            )
        
        return suggestions
    
    def get_update_history(
        self,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[InstructionUpdate]:
        """Get update history, optionally filtered by category"""
        history = self.update_history
        
        if category:
            history = [u for u in history if u.category == category]
        
        return history[-limit:]
    
    def rollback_update(self, update_id: str) -> bool:
        """Rollback a specific update"""
        for update in self.update_history:
            if update.id == update_id and update.applied and update.old_instruction:
                try:
                    name = update.new_instruction.get("name", update.category)
                    self.instructions[name] = update.old_instruction
                    update.applied = False
                    logger.info(f"Rolled back update: {update_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to rollback: {e}")
                    return False
        return False
    
    def export_history(self, format: str = "json") -> str:
        """Export update history"""
        if format == "json":
            return json.dumps(
                [asdict(update) for update in self.update_history],
                default=str,
                indent=2,
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
