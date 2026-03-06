"""
Example 1: Basic Task Execution
Demonstrates simple task execution and result retrieval
"""

import asyncio
from jarvis_os import JarvisOS, AgentConfig
from fast_router import TaskPriority


async def main():
    print("=" * 60)
    print("Jarvis-OS Example 1: Basic Task Execution")
    print("=" * 60)
    
    # Create agent configuration
    config = AgentConfig(
        name="example-1-agent",
        version="1.0.0",
        max_workers=5,
        task_timeout=30.0,
        memory_size=500,
        log_level="INFO",
        auto_optimize=False,  # Disable for this example
    )
    
    # Initialize and start agent
    agent = JarvisOS(config)
    await agent.start()
    print(f"\n✓ Agent '{config.name}' started")
    
    # Define a simple async task
    async def calculate(x, y):
        """Simple calculation task"""
        await asyncio.sleep(0.1)  # Simulate work
        return {"sum": x + y, "product": x * y}
    
    # Define a synchronous task
    def process_string(text):
        """Simple string processing task"""
        return {"original": text, "uppercase": text.upper(), "length": len(text)}
    
    # Execute individual tasks
    print("\n--- Executing Tasks ---")
    
    result1 = await agent.execute_task(
        task_type="calculation",
        task_func=calculate,
        task_params={"args": [10, 20]},
        priority=TaskPriority.NORMAL,
    )
    print(f"Task 1 (calculation): {result1.result}")
    print(f"  - Status: {result1.status.value}")
    print(f"  - Execution time: {result1.execution_time:.4f}s")
    
    result2 = await agent.execute_task(
        task_type="text_processing",
        task_func=process_string,
        task_params={"args": ["hello jarvis"]},
        priority=TaskPriority.HIGH,
    )
    print(f"\nTask 2 (text_processing): {result2.result}")
    print(f"  - Status: {result2.status.value}")
    print(f"  - Execution time: {result2.execution_time:.4f}s")
    
    # Get agent status
    print("\n--- Agent Status ---")
    status = agent.get_status()
    print(f"Agent: {status['name']}")
    print(f"Running: {status['running']}")
    print(f"Executor stats:")
    for key, value in status['executor_stats'].items():
        print(f"  - {key}: {value}")
    
    await agent.stop()
    print(f"\n✓ Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
