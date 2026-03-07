"""
Executor - Core task execution component
Handles the actual execution of tasks and performance monitoring
"""

import asyncio
import time
import uuid
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)



class CircuitBreakerError(Exception):
    pass

class CircuitBreaker:
    """Gap 12: Circuit breaker for latency budget"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return True

global_circuit_breaker = CircuitBreaker()

class Executor:
    """
    Core executor component responsible for task execution
    Handles concurrent execution, error handling, and performance monitoring
    """
    
    def __init__(self, max_workers: int = 10, timeout: float = 300.0, db=None):
        """
        Initialize executor
        
        Args:
            max_workers: Maximum concurrent tasks
            timeout: Task execution timeout in seconds
            db: Optional JarvisDatabase instance for persistence
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.db = db
        self.tasks: Dict[str, TaskResult] = {}
        self.semaphore = asyncio.Semaphore(max_workers)
        self.task_queue: asyncio.Queue = None
        self.running = False
        
    async def execute(
        self,
        func: Callable,
        *args,
        task_id: Optional[str] = None,
        **kwargs
    ) -> TaskResult:
        """
        Execute a task asynchronously
        
        Args:
            func: Callable to execute
            task_id: Optional task identifier
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            TaskResult containing execution outcome
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
        )
        

        if not global_circuit_breaker.can_execute():
            result.status = TaskStatus.FAILED
            result.error = "Circuit Breaker OPEN - Routing to cloud fallback"
            return result

        latency_budget = kwargs.pop('latency_budget', self.timeout)
        try:
            async with self.semaphore:

                result.status = TaskStatus.RUNNING
                start_time = time.time()
                
                # Execute with timeout
                try:
                    if asyncio.iscoroutinefunction(func):
                        result.result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.timeout
                        )
                    else:
                        result.result = await asyncio.wait_for(
                            asyncio.to_thread(func, *args, **kwargs),
                            timeout=self.timeout
                        )
                    result.status = TaskStatus.COMPLETED
                except asyncio.TimeoutError:
                    result.status = TaskStatus.FAILED
                    result.error = f"Task timeout after {self.timeout}s"
                    
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            logger.error(f"Task {task_id} failed: {e}")
        
        finally:
            result.execution_time = time.time() - start_time
            self.tasks[task_id] = result
            if self.db:
                # Fire and forget if we are in event loop
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.db.save_task(result))
                except RuntimeError:
                    pass
            
        return result
        
    async def load_state(self):
        """Load persistent state from database"""
        if self.db:
            db_tasks = await self.db.get_all_tasks()
            self.tasks.update(db_tasks)
    
    async def execute_batch(
        self,
        tasks: Dict[str, tuple]
    ) -> Dict[str, TaskResult]:
        """
        Execute multiple tasks concurrently
        
        Args:
            tasks: Dict mapping task_id to (func, args, kwargs) tuple
            
        Returns:
            Dict mapping task_id to TaskResult
        """
        results = {}
        
        async def execute_task_wrapper(task_id, func, args, kwargs):
            results[task_id] = await self.execute(func, *args, **kwargs)
        
        # Create all tasks
        coroutines = [
            execute_task_wrapper(task_id, func, args or (), kwargs or {})
            for task_id, (func, args, kwargs) in tasks.items()
        ]
        
        # Execute concurrently
        await asyncio.gather(*coroutines)
        
        return results
    
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result of a completed task"""
        if self.db:
            res_dict = await self.db.get_task_result(task_id)
            if res_dict:
                return TaskResult(
                    task_id=res_dict["task_id"],
                    status=TaskStatus(res_dict["status"]),
                    result=res_dict["result"],
                    error=res_dict["error"],
                    execution_time=res_dict["execution_time"],
                    timestamp=res_dict["timestamp"],
                    metadata=res_dict["metadata"],
                )
        return self.tasks.get(task_id)
    
    async def get_all_results(self) -> Dict[str, TaskResult]:
        """Get all task results"""
        if self.db:
            db_tasks = await self.db.get_all_tasks()
            # Merge with in-memory just in case
            merged = self.tasks.copy()
            merged.update(db_tasks)
            return merged
        return self.tasks.copy()
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        all_tasks = await self.get_all_results() if self.db else self.tasks
        if not all_tasks:
            return {
                "total_tasks": 0,
                "completed": 0,
                "failed": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
            }
        
        completed = sum(1 for t in all_tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in all_tasks.values() if t.status == TaskStatus.FAILED)
        avg_time = sum(t.execution_time for t in all_tasks.values()) / len(all_tasks)
        
        return {
            "total_tasks": len(all_tasks),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(all_tasks) if all_tasks else 0,
            "avg_execution_time": avg_time,
        }
    
    async def clear_completed_tasks(self, older_than: Optional[float] = None):
        """
        Clear completed tasks
        
        Args:
            older_than: Optional time threshold (seconds) to clear only older tasks
        """
        current_time = time.time()
        to_remove = []
        
        for task_id, result in self.tasks.items():
            if result.status == TaskStatus.COMPLETED:
                if older_than is None or (current_time - result.timestamp) > older_than:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
