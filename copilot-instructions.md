# Copilot Instructions for Jarvis-OS

This document provides Copilot with essential context for working efficiently in the Jarvis-OS repository. It describes the build/test process, high-level architecture, and key coding conventions used throughout the codebase.

## Build, Test, and Lint Commands

### Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (includes dev tools)
pip install -r requirements.txt

# One-time validation
python validate.py
```

### Running Tests

```bash
# Run all tests with verbose output
pytest test_jarvis_os.py -v

# Run a specific test class
pytest test_jarvis_os.py::TestExecutor -v

# Run a specific test
pytest test_jarvis_os.py::TestExecutor::test_execute_simple_task -v

# Run with coverage report
pytest test_jarvis_os.py --cov=. --cov-report=html

# Run with asyncio support (required)
pytest test_jarvis_os.py -v -m asyncio
```

### Linting and Code Quality

```bash
# Format code with Black
black *.py

# Lint with Pylint
pylint *.py

# Type checking with MyPy
mypy *.py

# All-in-one check
black *.py && pylint *.py && mypy *.py
```

### Validation Script

```bash
# Run comprehensive system validation (checks all modules, imports, interactions)
python validate.py
```

This script imports all 7 core modules, verifies component interactions, and reports the system status. Run this after making changes to core modules to ensure nothing broke.

---

## High-Level Architecture

Jarvis-OS is a **self-improving AI agent framework** built on event-driven task routing and continuous analysis/optimization.

### Component Hierarchy

```
JarvisOS (Orchestrator)
├── FastRouter
│   ├── Routes incoming tasks by type
│   ├── Maintains executor registry
│   └── Applies priority boosting
│
├── Executor
│   ├── Executes tasks concurrently (asyncio)
│   ├── Enforces timeouts via semaphores
│   └── Tracks execution stats
│
├── MemoryManager
│   ├── Short-term LRU cache (fast, bounded)
│   └── Long-term JSON storage (persistent)
│
├── StructuredLogger
│   ├── Records all task execution as JSON
│   ├── Tracks performance metrics
│   └── Writes to log file for analysis
│
├── Autopsy
│   ├── Analyzes historical logs (post-session)
│   ├── Identifies error patterns and hotspots
│   └── Generates improvement suggestions
│
└── Mutation
    ├── Applies suggestions from Autopsy
    ├── Generates InstructionUpdate objects
    ├── Modifies agent instructions.md
    └── Tracks update history
```

### Data Flow: Task Execution → Analysis → Self-Improvement

```
1. User submits task → JarvisOS.execute_task()
2. FastRouter classifies by task_type → selects Executor
3. Executor runs task async with timeout → TaskResult
4. StructuredLogger records: task_id, status, execution_time, error
5. [Session ends]
6. Autopsy.analyze() scans logs → finds patterns
7. Mutation.generate_update() creates improvement suggestions
8. New suggestions modify instructions.md
9. Next session uses updated instructions
```

### Key Design Principles

- **Zero-dependency core**: All 7 modules use only Python standard library (asyncio, json, logging, dataclasses, enum, uuid)
- **Fail gracefully**: Task failures are isolated; one crashed task doesn't crash the agent
- **Async-first**: Uses asyncio for concurrency; no threading in core logic
- **Observable**: Every action logged as JSON; full audit trail
- **Self-correcting**: Autopsy + Mutation create a feedback loop that improves over time

---

## Key Conventions

### 1. Module Organization

Each core module follows this pattern:

```python
"""Module docstring (one-liner purpose)"""

import asyncio
import json
# Standard library only in core modules
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Data classes (immutable, serializable)
@dataclass
class MyData:
    field: str
    count: int = 0

# Main class
class MyComponent:
    """Class docstring (responsibility)"""
    
    def __init__(self, config):
        """Initialize component"""
        self.config = config
    
    async def process(self):
        """Public method (docstring required)"""
        pass
```

**Why this matters**: 
- Dataclasses are serialized to JSON for logging
- Logging is structured to enable Autopsy analysis
- Async methods allow concurrent task execution

### 2. Logging Convention

Use structured logging with JSON-compatible data:

```python
# Good - flat structure, JSON-serializable
logger.info(f"Task {task_id} completed", extra={
    "task_id": task_id,
    "status": "completed",
    "duration_ms": 123.5,
    "result_size": len(result)
})

# Avoid - nested objects, non-JSON-serializable
logger.info(f"Task failed: {exception_obj}")  # Object not serializable!
```

All logged fields must be JSON-serializable (str, int, float, bool, list, dict, null).

### 3. Async Task Pattern

When executing user-provided functions:

```python
# Wrap sync functions in asyncio.to_thread to avoid blocking
async def execute_user_task(task_func, task_id, timeout):
    try:
        if asyncio.iscoroutinefunction(task_func):
            result = await asyncio.wait_for(
                task_func(),
                timeout=timeout
            )
        else:
            # Run sync function in thread pool
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, task_func),
                timeout=timeout
            )
        return TaskResult(status=TaskStatus.COMPLETED, result=result)
    except asyncio.TimeoutError:
        return TaskResult(status=TaskStatus.FAILED, error="Task timeout")
    except Exception as e:
        return TaskResult(status=TaskStatus.FAILED, error=str(e))
```

**Why**: Ensures user code (sync or async) runs safely with timeout protection.

### 4. Memory Storage Convention

Use consistent key naming for memory operations:

```python
# Key format: "namespace:identifier:subtype"
# Examples:
"session:uuid-123:context"              # Session metadata
"user:alice:preferences"                # User preferences
"error:powershell:command_not_found"    # Error pattern
"model:phi3:router_v2"                  # Cached model

# Always use string keys and JSON-serializable values
agent.memory.store(
    key="session:abc123:transcript",
    value={"messages": [...]},           # Dict, not object
    persistent=True,
    ttl=86400  # 24 hours
)
```

### 5. Mutation and Instruction Updates

When the Mutation engine creates updates:

```python
# InstructionUpdate structure
update = InstructionUpdate(
    id=str(uuid.uuid4()),
    timestamp=time.time(),
    category="routing",  # routing, error_handling, performance, memory, etc.
    priority="high",     # low, medium, high, critical
    description="Route PowerShell tasks to cloud executor",
    old_instruction={"executor_type": "local"},
    new_instruction={"executor_type": "cloud", "fallback": "local"},
    reasoning="Local timeouts increased 40% after 2 PM",
    confidence_score=0.82,
    applied=False
)
```

**Why**: Autopsy searches mutations by category; confidence scores drive approval decisions.

### 6. Router Rule Pattern

When adding routing rules:

```python
from fast_router import FastRouter, TaskPriority

router = agent.router

# Define a matcher function (predicate)
def is_compute_heavy(task_type: str, params: dict) -> bool:
    """Return True if task matches this rule"""
    return task_type.startswith("compute") and params.get("data_size_mb", 0) > 100

# Register executor
router.register_executor("gpu_executor", gpu_exec_instance)

# Add route
router.add_route(
    name="gpu_compute",
    matcher=is_compute_heavy,
    executor_id="gpu_executor",
    priority_boost=2  # Execute before normal-priority tasks
)
```

**Why**: Router evaluates matchers in registration order; first match wins. Use `priority_boost` to force urgent tasks through.

### 7. Batch Task Execution

When executing multiple tasks:

```python
# Pass dict of {task_name: (function, args, kwargs)}
tasks = {
    "fetch_1": (async_fetch, ("https://api1.com",), {}),
    "fetch_2": (async_fetch, ("https://api2.com",), {}),
    "parse": (parse_results, (), {"format": "json"})
}

results = await agent.execute_batch(tasks, priority=TaskPriority.HIGH)

# Results dict: {task_name: TaskResult}
for name, result in results.items():
    if result.status == TaskStatus.COMPLETED:
        print(f"{name}: {result.result}")
    else:
        print(f"{name} FAILED: {result.error}")
```

---

## Configuration Patterns

### AgentConfig Usage

```python
from jarvis_os import AgentConfig, JarvisOS

# Typical production config
config = AgentConfig(
    name="voice-agent",
    version="1.0.0",
    max_workers=10,         # Concurrent task limit; 2x CPU cores for I/O tasks
    task_timeout=300.0,     # 5 minutes (increase for long-running tasks)
    memory_size=1000,       # LRU cache entries
    log_level="INFO",       # DEBUG for development, INFO for production
    auto_optimize=True,     # Enable self-improvement loop
    optimization_interval=300.0,  # Run Autopsy/Mutation every 5 min
    error_threshold=0.1,    # Flag if error rate > 10%
    performance_threshold=5.0  # Flag if avg time > 5 sec
)

agent = JarvisOS(config)
```

### Environment-Specific Tuning

```python
import os

if os.getenv("ENV") == "production":
    config = AgentConfig(
        name="prod-agent",
        max_workers=50,         # More concurrency
        task_timeout=600.0,     # More lenient timeout
        memory_size=5000,       # Larger cache
        log_level="WARNING"     # Less verbose
    )
else:
    config = AgentConfig(
        name="dev-agent",
        max_workers=5,
        task_timeout=30.0,      # Stricter for faster feedback
        memory_size=100,
        log_level="DEBUG"
    )
```

---

## Common Task Patterns

### Simple Sequential Task

```python
async def simple_task_example():
    config = AgentConfig(name="simple")
    agent = JarvisOS(config)
    await agent.start()
    
    async def my_task():
        return "Hello from Jarvis"
    
    result = await agent.execute_task(
        task_type="greeting",
        task_func=my_task
    )
    
    print(f"Result: {result.result}")
    print(f"Time: {result.execution_time}s")
    
    await agent.stop()
```

### Conditional Task Routing

```python
# Route based on input characteristics
def route_handler(user_input: str):
    if len(user_input) > 1000:
        return "long_form_analysis"  # Route to slower, thorough handler
    elif user_input.startswith("@"):
        return "command_execution"   # Route to executor
    else:
        return "quick_response"      # Route to cached handler

# Then define executors for each route
router.add_route(
    name="by_input_size",
    matcher=lambda tt, p: route_handler(p.get("input", "")) == tt,
    executor_id="appropriate_executor"
)
```

### Memory-Aware Task

```python
async def memory_aware_task(agent, user_id):
    # Retrieve user context
    context = agent.memory.retrieve(f"user:{user_id}:context")
    
    if context is None:
        context = {"interaction_count": 0}
    
    # Execute task with context
    result = await agent.execute_task(
        task_type="user_request",
        task_func=lambda: process_with_context(context)
    )
    
    # Update memory
    context["interaction_count"] += 1
    agent.memory.store(
        key=f"user:{user_id}:context",
        value=context,
        persistent=True,
        ttl=604800  # 7 days
    )
    
    return result
```

---

## When to Extend vs. When Not To

### Good extensions (follow these patterns)

- Add new executor types via `router.register_executor()`
- Add routing rules via `router.add_route()`
- Store new memory keys following `namespace:id:type` convention
- Create new task types (string identifiers)
- Add custom fields to `InstructionUpdate` (backward compatible)

### Avoid changing

- Core method signatures in Executor, Router, MemoryManager, StructuredLogger
- JSON serialization format for logs (Autopsy depends on it)
- The `TaskResult` dataclass structure (it's the contract with users)
- Mutation categories (existing rules reference them)

If you need to change these, it's a breaking change—update all usages and bump version.

---

## Testing Tips

### Test Pattern: Async Test with Fixtures

```python
import pytest

class TestMyFeature:
    @pytest.fixture
    def agent(self):
        config = AgentConfig(name="test-agent", max_workers=2)
        agent = JarvisOS(config)
        return agent
    
    @pytest.mark.asyncio
    async def test_my_feature(self, agent):
        await agent.start()
        
        result = await agent.execute_task(
            task_type="test",
            task_func=lambda: "success"
        )
        
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "success"
        
        await agent.stop()
```

### Mocking Executors in Tests

```python
# Create a mock executor for testing
from executor import Executor, TaskStatus, TaskResult

async def mock_executor_task():
    return TaskResult(
        task_id="mock-123",
        status=TaskStatus.COMPLETED,
        result={"mocked": True},
        execution_time=0.001
    )
```

---

## Performance Considerations

### Key Metrics to Monitor

- **Router latency**: Should be <1ms (pattern matching overhead)
- **Task execution time**: Highly variable; enforce `task_timeout` to prevent hangs
- **Memory cache hit rate**: Track via `agent.memory.get_stats()["hit_rate"]`
- **Autopsy analysis time**: ~0.5-1s per 1000 log entries
- **Mutation application time**: Negligible unless updating large instructions file

### Scaling Guidance

- **CPU-bound tasks**: Set `max_workers = os.cpu_count()` (typically 4-16)
- **I/O-bound tasks**: Set `max_workers = 50-100` (thread pool can handle many waiting tasks)
- **Memory-intensive tasks**: Set `max_workers = 5`, increase `memory_size` carefully
- **Batch size**: Keep `execute_batch()` under 100 tasks; split larger batches

---

## Architecture Decision: Why These Choices?

### Why Async (asyncio) Not Threading?

- Async scales to thousands of I/O tasks on a single thread
- No mutex complexity; avoids deadlock bugs
- Better integration with existing Python ecosystem
- Lower memory overhead (~1KB per coroutine vs ~1MB per thread)

### Why JSON Logs Not Binary?

- Human-readable for debugging
- Easy to analyze with standard tools (jq, grep)
- Forward-compatible; schema changes don't break old logs
- Enables streaming analysis (Autopsy can process while still logging)

### Why LRU Cache + JSON File, Not Redis?

- Zero external dependencies; deployable anywhere
- Simpler debugging; data is local
- Sufficient for single-machine use cases
- Easy migration to Redis later (just swap MemoryManager backend)

### Why Router Rules Not ML?

- Deterministic; no training needed
- Fast; <1ms per decision
- Explainable; audit trail shows which rule matched
- Can be upgraded to ML later (keep fallback to rules)

---

## Links and References

- **Full API Reference**: See `README_FULL.md`
- **Architecture Deep Dive**: See `IMPLEMENTATION_SUMMARY.md`  
- **Getting Started**: See `GETTING_STARTED.md`
- **Examples**: Run `python example_*.py` files
- **Tests**: Review `test_jarvis_os.py` for patterns
- **Validation**: Run `python validate.py` to check system integrity

---

## Quick Checklist for Contributors

Before submitting changes:

- [ ] Code follows conventions above (dataclasses, async patterns, logging)
- [ ] All public methods have docstrings
- [ ] Logging uses JSON-compatible fields
- [ ] Changes are backward compatible (don't break existing Task/Result contracts)
- [ ] Tests pass: `pytest test_jarvis_os.py -v`
- [ ] Validation passes: `python validate.py`
- [ ] Code formatted with Black: `black *.py`
- [ ] No new external dependencies added to core modules

---

**Last Updated**: 2026-03-07  
**Version**: 1.0.0
