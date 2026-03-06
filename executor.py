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


class Executor:
    """
    Core executor component responsible for task execution
    Handles concurrent execution, error handling, and performance monitoring
    """
    
    def __init__(self, max_workers: int = 10, timeout: float = 300.0):
        """
        Initialize executor
        
        Args:
            max_workers: Maximum concurrent tasks
            timeout: Task execution timeout in seconds
        """
        self.max_workers = max_workers
        self.timeout = timeout
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
            
        return result
    
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
    
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result of a completed task"""
        return self.tasks.get(task_id)
    
    def get_all_results(self) -> Dict[str, TaskResult]:
        """Get all task results"""
        return self.tasks.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.tasks:
            return {
                "total_tasks": 0,
                "completed": 0,
                "failed": 0,
                "avg_execution_time": 0.0,
            }
        
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        avg_time = sum(t.execution_time for t in self.tasks.values()) / len(self.tasks)
        
        return {
            "total_tasks": len(self.tasks),
            "completed": completed,
            "failed": failed,
            "success_rate": completed / len(self.tasks) if self.tasks else 0,
            "avg_execution_time": avg_time,
        }
    
    def clear_completed_tasks(self, older_than: Optional[float] = None):
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
