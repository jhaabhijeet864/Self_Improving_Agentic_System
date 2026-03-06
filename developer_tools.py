"""
CLI Executor - Terminal Execution Wrapper for Swara AI
Safely runs terminal commands as Jarvis-OS tasks, capturing stdout/stderr
and strictly enforcing timeouts to prevent hanging processes.
"""

import asyncio
import logging
import shlex
import time
import uuid
from typing import Optional, Dict, Any

from executor import Executor, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

class CLIExecutor(Executor):
    """
    Executor specifically designed to safely run shell commands.
    Perfect for Swara AI when it acts as a Developer Agent.
    """
    
    async def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        task_id: Optional[str] = None
    ) -> TaskResult:
        """
        Execute a shell command via asyncio.create_subprocess_shell
        
        Args:
            command: The raw shell command (e.g., 'npm run build').
            cwd: Current Working Directory to run the command in.
            env: Environment variables to inject.
            task_id: Optional UUID.
        """
        if task_id is None:
            task_id = str(uuid.uuid4())
            
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        
        try:
            async with self.semaphore:
                result.status = TaskStatus.RUNNING
                start_time = time.time()
                
                logger.info(f"Executing CLI Command: '{command}'")
                
                # Create the subprocess
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env
                )
                
                try:
                    # Wait for completion, bounded by our strict timeout
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.timeout
                    )
                    
                    stdout = stdout_bytes.decode('utf-8').strip() if stdout_bytes else ""
                    stderr = stderr_bytes.decode('utf-8').strip() if stderr_bytes else ""
                    
                    if process.returncode == 0:
                        result.status = TaskStatus.COMPLETED
                        result.result = {
                            "command": command,
                            "stdout": stdout,
                            "stderr": stderr,
                            "exit_code": process.returncode
                        }
                    else:
                        result.status = TaskStatus.FAILED
                        # Pass stderr to `error` so Autopsy logs it for Mutation!
                        result.error = f"Exit code {process.returncode}. Stderr: {stderr}"
                        result.metadata = {"stdout": stdout} # Still capture partial stdout
                        
                except asyncio.TimeoutError:
                    # The command hung! (e.g., live server, stuck prompt)
                    # We MUST kill it to save Swara AI
                    try:
                        process.terminate()
                        await asyncio.sleep(0.1)
                        if process.returncode is None:
                            process.kill()
                    except ProcessLookupError:
                        pass
                        
                    result.status = TaskStatus.FAILED
                    result.error = f"CLI task timed out after {self.timeout}s and was killed."
                    logger.warning(f"Killed hanging process: '{command}'")
                    
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            logger.error(f"CLI Executor task {task_id} failed to launch: {e}")
            
        finally:
            result.execution_time = time.time() - start_time
            self.tasks[task_id] = result
            
        return result


import functools
from typing import Callable
from jarvis_os import JarvisOS

def jarvis_tool(agent: JarvisOS, task_type: str, priority=None):
    """
    Decorator to effortlessly register Swara AI functions into Jarvis-OS.
    Any function decorated with this will automatically be 
    executed via `agent.execute_task()` instead of running raw.
    
    Args:
        agent: The JarvisOS instance to bind this tool to.
        task_type: The string identifier for routing (e.g., 'file_writer').
        priority: Optional FastRouter task priority.
    """
    def decorator(func: Callable):
        # Register the raw function as a native capable route
        # (Assuming you want all tools to hit the default Executor for simplicity)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from fast_router import TaskPriority
            eff_priority = priority or TaskPriority.NORMAL
            
            logger.info(f"[{task_type}] Intercepted method call '{func.__name__}', routing to Jarvis...")
            result = await agent.execute_task(
                task_type=task_type,
                task_func=func,
                task_params={"args": args, "kwargs": kwargs},
                priority=eff_priority
            )
            
            # If the task failed inside Jarvis, raise the caught exception
            if result.status.value != "completed":
                raise RuntimeError(f"Jarvis Tool '{func.__name__}' Failed: {result.error}")
                
            return result.result
            
        return wrapper
    return decorator


import tempfile
import os
import sys

class SandboxManager:
    """
    Safety wrapper to evaluate AI-generated code strings.
    Swara AI can use this to 'test' python logic before writing it to a project.
    """
    
    def __init__(self, agent: JarvisOS):
        self.agent = agent
        # We use a CLIExecutor for the sandbox to get timeout/crash protection
        self.sandbox_executor = CLIExecutor(max_workers=5, timeout=10.0)
        
    async def evaluate_code(self, python_code_string: str) -> Dict[str, Any]:
        """
        Write code to a temporary file, run it, and capture the output safely.
        """
        # 1. Create a secure temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(python_code_string)
            temp_path = temp_file.name
            
        try:
            # 2. Ask the CLI Executor to run the temp script using the current python interpreter
            sandbox_command = f'"{sys.executable}" "{temp_path}"'
            
            # 3. Route through Jarvis-OS (indirectly) or just use our secure nested Executor
            result = await self.sandbox_executor.execute_command(sandbox_command)
            
            if result.status.value == "completed" and isinstance(result.result, dict):
                return {
                    "success": True,
                    "stdout": result.result.get("stdout", ""),
                    "stderr": result.result.get("stderr", "")
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "stdout": result.metadata.get("stdout", "") if result.metadata else ""
                }
                
        finally:
            # 4. Cleanup the physical temp file always
            if os.path.exists(temp_path):
                os.remove(temp_path)
