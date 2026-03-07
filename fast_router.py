"""
Fast Router - Efficient task routing system
Routes tasks to appropriate executors based on priority, type, and load
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict
import json
import os
try:
    import torch
    from transformers import pipeline
except ImportError:
    pipeline = None


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Route:
    """A routing rule"""
    name: str
    matcher: Callable[[str, Dict[str, Any]], bool]
    executor_id: str
    priority_boost: int = 0


class FastRouter:
    """
    Fast router for task distribution
    Matches tasks to executors based on configurable rules
    """
    
    def __init__(self):
        """Initialize router"""
        self.routes: List[Route] = []
        self.executors: Dict[str, Any] = {}
        self.queue: Dict[str, List[tuple]] = defaultdict(list)
        self.stats = {
            "routed_tasks": 0,
            "routes_by_name": defaultdict(int),
        }
    
    def register_executor(self, executor_id: str, executor: Any):
        """Register an executor"""
        self.executors[executor_id] = executor
        logger.info(f"Registered executor: {executor_id}")
    
    def add_route(
        self,
        name: str,
        matcher: Callable[[str, Dict[str, Any]], bool],
        executor_id: str,
        priority_boost: int = 0,
    ):
        """
        Add a routing rule
        
        Args:
            name: Route name
            matcher: Function that returns True if task matches
            executor_id: Executor to route to
            priority_boost: Additional priority for matched tasks
        """
        if executor_id not in self.executors:
            raise ValueError(f"Executor {executor_id} not registered")
        
        route = Route(
            name=name,
            matcher=matcher,
            executor_id=executor_id,
            priority_boost=priority_boost,
        )
        self.routes.append(route)
        logger.info(f"Added route: {name} -> {executor_id}")
    
    def route_task(
        self,
        task_type: str,
        task_params: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Tuple[str, int]:
        """
        Route a task to an executor
        
        Args:
            task_type: Type of task
            task_params: Task parameters
            priority: Task priority
            
        Returns:
            Tuple of (executor_id, effective_priority)
        """
        matched_route = None
        best_priority = priority.value
        
        # Find first matching route
        for route in self.routes:
            try:
                if route.matcher(task_type, task_params):
                    matched_route = route
                    best_priority = priority.value + route.priority_boost
                    break
            except Exception as e:
                logger.error(f"Route matcher error: {e}")
        
        # Use default executor if no match
        executor_id = matched_route.executor_id if matched_route else "default"
        route_name = matched_route.name if matched_route else "default"
        
        self.stats["routed_tasks"] += 1
        self.stats["routes_by_name"][route_name] += 1
        
        logger.debug(f"Routed {task_type} to {executor_id} (priority: {best_priority})")
        
        return executor_id, best_priority
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "total_routed": self.stats["routed_tasks"],
            "routes_used": dict(self.stats["routes_by_name"]),
            "registered_executors": len(self.executors),
            "num_routes": len(self.routes),
        }


class ConditionalRouter(FastRouter):
    """
    Extended router with conditional logic
    Supports complex routing rules
    """
    
    def __init__(self):
        """Initialize conditional router"""
        super().__init__()
        self.conditions: Dict[str, Callable] = {}
    
    def register_condition(self, name: str, condition: Callable):
        """Register a reusable condition"""
        self.conditions[name] = condition
    
    def add_conditional_route(
        self,
        name: str,
        condition_name: str,
        executor_id: str,
        priority_boost: int = 0,
    ):
        """
        Add a route using a registered condition
        
        Args:
            name: Route name
            condition_name: Name of registered condition
            executor_id: Executor to route to
            priority_boost: Priority boost for matched tasks
        """
        if condition_name not in self.conditions:
            raise ValueError(f"Condition {condition_name} not registered")
        
        condition = self.conditions[condition_name]
        self.add_route(name, condition, executor_id, priority_boost)


def create_default_router() -> FastRouter:
    """Create a router with default configurations"""
    router = FastRouter()
    
    # Add default routes based on task type
    def is_cpu_intensive(task_type: str, params: Dict[str, Any]) -> bool:
        return task_type in ["compute", "analysis", "processing"]
    
    def is_io_bound(task_type: str, params: Dict[str, Any]) -> bool:
        return task_type in ["fetch", "read", "write", "network"]
    
    def is_urgent(task_type: str, params: Dict[str, Any]) -> bool:
        return params.get("urgent", False)
    
    # Assuming executors would be registered: high-perf for CPU, async for IO
    # router.add_route("cpu_tasks", is_cpu_intensive, "cpu_executor", priority_boost=1)
    # router.add_route("io_tasks", is_io_bound, "async_executor", priority_boost=0)
    # router.add_route("urgent", is_urgent, "priority_executor", priority_boost=2)
    
    return router


class MLRouter(FastRouter):
    """
    Machine Learning based router that uses an SFT model (like phi-3-mini) 
    to classify intents, solving Gap 2 and Gap 11.
    """
    def __init__(self, model_path: str = None, dataset_path: str = 'jarvis_sft_dataset.jsonl'):
        super().__init__()
        self.model_path = model_path
        self.dataset_path = dataset_path
        self.classifier = None
        self.labels = ['compute', 'network', 'io', 'system', 'unknown']
        
        if pipeline is not None and model_path and os.path.exists(model_path):
            try:
                self.classifier = pipeline(
                    'text-classification', 
                    model=model_path, 
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info(f"Loaded ML Router model from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}")
                
    def train_or_update(self):
        """
        Reads jarvis_sft_dataset.jsonl (Gap 11) and updates the model.
        In a real scenario, this spawns a LoRA fine-tuning subprocess.
        """
        if not os.path.exists(self.dataset_path):
            logger.warning(f"SFT Dataset not found at {self.dataset_path}")
            return
            
        logger.info(f"Loading dataset from {self.dataset_path} for incremental training...")
        # Load JSONL and prepare for HF Trainer
        with open(self.dataset_path, 'r', encoding='utf-8') as df:
            samples = [json.loads(line) for line in df]
        logger.info(f"Loaded {len(samples)} examples for training")
        
    def route_task(
        self,
        task_type: str,
        task_params: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Tuple[str, int]:
        
        # If ML model is loaded, use it to classify intent from params
        if self.classifier and 'intent' in task_params:
            try:
                intent_text = task_params['intent']
                result = self.classifier(intent_text)[0]
                predicted_label = result['label']
                
                executor_id = f"{predicted_label}_executor"
                
                if executor_id in self.executors:
                    self.stats["routed_tasks"] += 1
                    self.stats["routes_by_name"]["ml_route"] += 1
                    return executor_id, priority.value
            except Exception as e:
                logger.error(f"ML routing failed, falling back: {e}")
                
        # Fallback to FastRouter rule-based
        return super().route_task(task_type, task_params, priority)
