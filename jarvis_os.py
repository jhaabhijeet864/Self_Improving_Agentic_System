"""
Jarvis-OS - Main agent class
Orchestrates all components for production-scale AI operations
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import logging

from executor import Executor, TaskStatus, TaskResult
from autopsy import Autopsy, LogEntry
from mutation import Mutation
from memory_manager import MemoryManager
from fast_router import FastRouter, TaskPriority
from structured_logger import StructuredLogger


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for JarvisOS agent"""
    name: str
    version: str = "1.0.0"
    max_workers: int = 10
    task_timeout: float = 300.0
    memory_size: int = 1000
    log_level: str = "INFO"
    auto_optimize: bool = True
    optimization_interval: float = 300.0  # 5 minutes
    error_threshold: float = 0.1  # 10%
    performance_threshold: float = 5.0  # 5 seconds


class JarvisOS:
    """
    Main Jarvis-OS Agent
    Orchestrates Executor, Autopsy, Mutation, Memory, and Router components
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize JarvisOS agent
        
        Args:
            config: AgentConfig containing agent settings
        """
        self.config = config
        self.logger = StructuredLogger(config.name, config.log_level)
        
        # Initialize components
        self.executor = Executor(
            max_workers=config.max_workers,
            timeout=config.task_timeout,
        )
        self.autopsy = Autopsy()
        self.mutation = Mutation()
        self.memory = MemoryManager(
            short_term_size=config.memory_size,
            long_term_file=f"{config.name}_memory.json",
        )
        self.router = FastRouter()
        
        self.running = False
        self.task_id_counter = 0
        self.last_optimization = time.time()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        self.logger.info(f"Initialized Jarvis-OS: {config.name}")
    
    async def start(self):
        """Start the agent"""
        self.running = True
        self.loop = asyncio.get_event_loop()
        self.logger.info("Agent started")
        
        if self.config.auto_optimize:
            # Start optimization loop
            asyncio.create_task(self._optimization_loop())
    
    async def stop(self):
        """Stop the agent"""
        self.running = False
        self.logger.info("Agent stopped")
    
    async def execute_task(
        self,
        task_type: str,
        task_func: Callable,
        task_params: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        persistent_memory: bool = False,
    ) -> TaskResult:
        """
        Execute a task
        
        Args:
            task_type: Type of task
            task_func: Function to execute
            task_params: Task parameters
            priority: Task priority
            persistent_memory: Whether to store result in persistent memory
            
        Returns:
            TaskResult
        """
        if task_params is None:
            task_params = {}
        
        # Generate task ID
        self.task_id_counter += 1
        task_id = f"{self.config.name}-{self.task_id_counter}"
        
        # Log task start
        self.logger.log_task_start(task_id, task_type, task_params)
        
        # Route task
        executor_id, effective_priority = self.router.route_task(
            task_type, task_params, priority
        )
        
        start_time = time.time()
        
        try:
            # Store task in memory
            self.memory.store(
                f"task:{task_id}",
                {"type": task_type, "params": task_params, "status": "running"},
                persistent=persistent_memory,
                priority=effective_priority,
            )
            
            # Execute task
            result = await self.executor.execute(
                task_func,
                *task_params.get("args", ()),
                task_id=task_id,
                **task_params.get("kwargs", {}),
            )
            
            execution_time = time.time() - start_time
            
            # Log task completion
            self.logger.log_task_complete(task_id, execution_time, result.result)
            
            # Store result in memory
            self.memory.store(
                f"task_result:{task_id}",
                result,
                persistent=persistent_memory,
                priority=effective_priority,
            )
            
            # Log to autopsy
            self.autopsy.add_log(LogEntry(
                timestamp=time.time(),
                level="INFO" if result.status == TaskStatus.COMPLETED else "ERROR",
                message=f"Task {task_id} {result.status.value}",
                task_id=task_id,
                duration=execution_time,
                status=result.status.value,
                error=result.error,
            ))
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.log_task_error(task_id, e, execution_time)
            
            # Log error
            self.autopsy.add_log(LogEntry(
                timestamp=time.time(),
                level="ERROR",
                message=f"Task {task_id} error: {str(e)}",
                task_id=task_id,
                duration=execution_time,
                status="error",
                error=str(e),
            ))
            
            raise
    
    async def execute_batch(
        self,
        tasks: Dict[str, tuple],
    ) -> Dict[str, TaskResult]:
        """
        Execute multiple tasks
        
        Args:
            tasks: Dict mapping task_id to (func, args, kwargs)
            
        Returns:
            Dict mapping task_id to TaskResult
        """
        return await self.executor.execute_batch(tasks)
    
    async def _optimization_loop(self):
        """Continuous self-optimization loop"""
        while self.running:
            try:
                current_time = time.time()
                if (current_time - self.last_optimization) > self.config.optimization_interval:
                    await self.optimize()
                    self.last_optimization = current_time
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Optimization loop error: {e}")
    
    async def optimize(self):
        """Perform self-optimization"""
        try:
            # Run analysis
            analysis = self.autopsy.analyze()
            
            self.logger.log_analysis("performance", {
                "error_rate": analysis.error_rate,
                "avg_execution_time": analysis.avg_execution_time,
                "total_tasks": analysis.total_entries,
            })
            
            # Generate suggestions
            suggestions = self.mutation.generate_suggestions({
                "error_rate": analysis.error_rate,
                "avg_execution_time": analysis.avg_execution_time,
                "patterns": analysis.patterns,
                "hotspots": analysis.hotspots,
            })
            
            # Apply high-confidence updates
            for suggestion in suggestions:
                if suggestion.confidence_score >= 0.8:
                    applied = self.mutation.apply_update(suggestion)
                    
                    self.logger.log_mutation(
                        suggestion.id,
                        suggestion.category,
                        suggestion.description,
                        suggestion.confidence_score,
                    )
            
            # Log performance metrics
            perf_stats = self.executor.get_performance_stats()
            self.logger.log_performance(
                "success_rate",
                perf_stats["success_rate"],
                unit="%",
            )
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "running": self.running,
            "uptime": time.time(),
            "executor_stats": self.executor.get_performance_stats(),
            "memory_stats": self.memory.get_stats(),
            "router_stats": self.router.get_stats(),
            "autopsy_analysis": {
                "error_rate": self.autopsy.get_error_rate(),
                "avg_time": self.autopsy.get_average_execution_time(),
            },
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics"""
        return {
            "performance": self.executor.get_performance_stats(),
            "memory": self.memory.get_stats(),
            "router": self.router.get_stats(),
            "analysis": self.autopsy.analyze(),
            "mutations": len(self.mutation.update_history),
        }


async def run_example():
    """Example usage of Jarvis-OS"""
    
    # Create agent
    config = AgentConfig(
        name="example-agent",
        version="1.0.0",
        max_workers=5,
        task_timeout=30.0,
        memory_size=500,
        log_level="INFO",
    )
    
    agent = JarvisOS(config)
    await agent.start()
    
    # Define a simple task
    async def process_data(data):
        await asyncio.sleep(0.1)
        return {"processed": data * 2}
    
    # Execute task
    try:
        result = await agent.execute_task(
            task_type="data_processing",
            task_func=process_data,
            task_params={"args": [42], "kwargs": {}},
            priority=TaskPriority.NORMAL,
        )
        print(f"Task result: {result.result}")
    except Exception as e:
        print(f"Task failed: {e}")
    
    # Get agent status
    status = agent.get_status()
    print(f"Agent status: {status}")
    
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(run_example())
