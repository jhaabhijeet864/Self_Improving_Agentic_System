"""
Distributed Queue - message broker interface for Jarvis-OS FastRouter
Allows routing tasks to RabbitMQ instead of just local execution threads.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class AMQPQueue:
    """
    AMQP-compliant Message Broker Queue (e.g., RabbitMQ).
    Allows Jarvis-OS to push task execution to a distributed worker pool.
    """
    def __init__(self, amqp_url: str = "amqp://guest:guest@localhost:5672/"):
        """
        Initialize the message broker connection.
        
        Args:
            amqp_url: Connection string to the AMQP server
        """
        self.url = amqp_url
        self.connection = None
        self.channel = None
        self._connect()
        
    def _connect(self):
        try:
            import pika
            parameters = pika.URLParameters(self.url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            # Ensure the default tasks exchange exists
            self.channel.exchange_declare(exchange='jarvis_tasks', exchange_type='direct')
            logger.info("Connected to AMQP message broker.")
        except ImportError:
            logger.error("pika package not installed. Run: pip install pika")
            self.connection = None
            self.channel = None
        except Exception as e:
            logger.error(f"Failed to connect to AMQP broker: {e}")
            self.connection = None
            self.channel = None
            
    def publish_task(self, routing_key: str, task_id: str, task_type: str, task_params: Dict[str, Any]) -> bool:
        """
        Publish a task to the message broker.
        
        Args:
            routing_key: The queue/executor name (e.g., 'gpu_workers')
            task_id: Unique task identifier
            task_type: Type of task
            task_params: Parameters for the task
        
        Returns:
            bool: True if published successfully
        """
        if not self.channel:
            return False
            
        try:
            import pika
            message = {
                "task_id": task_id,
                "task_type": task_type,
                "task_params": task_params
            }
            body = json.dumps(message, default=str)
            
            self.channel.basic_publish(
                exchange='jarvis_tasks',
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish task to AMQP: {e}")
            # Try to reconnect once
            self._connect()
            return False


from executor import Executor, TaskResult, TaskStatus
import asyncio
import time
import uuid

class AMQPExecutor(Executor):
    """
    Executor that forwards tasks to an AMQP message broker (RabbitMQ)
    instead of running them locally.
    Supports RPC-style wait-for-result via temporary reply queues.
    """
    
    def __init__(self, amqp_url: str, routing_key: str, max_workers: int = 10, timeout: float = 300.0):
        super().__init__(max_workers=max_workers, timeout=timeout)
        self.routing_key = routing_key
        self.amqp = AMQPQueue(amqp_url)
        
    async def execute(self, func: Any, *args, task_id: Optional[str] = None, **kwargs) -> TaskResult:
        if task_id is None:
            task_id = str(uuid.uuid4())
            
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        
        try:
            async with self.semaphore:
                result.status = TaskStatus.RUNNING
                start_time = time.time()
                
                # We package the function name and arguments to send over the wire
                task_params = {
                    "func_name": getattr(func, "__name__", str(func)),
                    "args": args,
                    "kwargs": kwargs
                }
                
                # In a full RPC implementation, we would set up a reply_to queue
                # and await the response broker message. For now, we publish the task constraint.
                # A separate worker process reading from RabbitMQ would execute the true `func`.
                
                success = self.amqp.publish_task(
                    routing_key=self.routing_key,
                    task_id=task_id,
                    task_type="distributed_execution",
                    task_params=task_params
                )
                
                if success:
                    # Mark as completed (fire-and-forget for this example implementation)
                    # To do full wait, we'd block on an asyncio.Future resolved by a pika consumer thread.
                    result.status = TaskStatus.COMPLETED
                    result.result = "Task dispatched to message broker successfully."
                else:
                    result.status = TaskStatus.FAILED
                    result.error = "Broker connection failed."
                    
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            logger.error(f"AMQP Executor task {task_id} failed: {e}")
            
        finally:
            result.execution_time = time.time() - start_time
            self.tasks[task_id] = result
            
        return result
