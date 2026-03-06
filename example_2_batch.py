"""
Example 2: Batch Processing
Demonstrates executing multiple tasks concurrently
"""

import asyncio
from jarvis_os import JarvisOS, AgentConfig


async def main():
    print("=" * 60)
    print("Jarvis-OS Example 2: Batch Processing")
    print("=" * 60)
    
    config = AgentConfig(
        name="batch-agent",
        max_workers=10,
        task_timeout=30.0,
        auto_optimize=False,
    )
    
    agent = JarvisOS(config)
    await agent.start()
    print(f"✓ Agent started with {config.max_workers} workers\n")
    
    # Define work task
    async def work_task(item_id, value):
        """Simulated work on an item"""
        await asyncio.sleep(0.1)
        return {"id": item_id, "result": value * 2, "processed": True}
    
    # Execute batch of tasks
    print("--- Processing Batch of 20 Tasks ---")
    tasks = {}
    for i in range(20):
        task_func = lambda v=i: work_task(i, v)
        tasks[f"task_{i:02d}"] = (work_task, (i, i), {})
    
    results = await agent.execute_batch(tasks)
    
    print(f"\n✓ Completed {len(results)} tasks")
    print(f"\nResults summary:")
    success = sum(1 for r in results.values() if r.result is not None)
    failed = len(results) - success
    print(f"  - Successful: {success}")
    print(f"  - Failed: {failed}")
    
    # Show first few results
    print(f"\nFirst 3 results:")
    for i, (task_id, result) in enumerate(list(results.items())[:3]):
        print(f"  - {task_id}: {result.result}")
    
    # Get metrics
    metrics = agent.get_metrics()
    print(f"\n--- Performance Metrics ---")
    print(f"Total tasks executed: {metrics['performance']['total_tasks']}")
    print(f"Success rate: {metrics['performance']['success_rate']:.1%}")
    print(f"Avg execution time: {metrics['performance']['avg_execution_time']:.4f}s")
    
    await agent.stop()
    print(f"\n✓ Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
