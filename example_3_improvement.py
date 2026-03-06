"""
Example 3: Self-Improvement Loop
Demonstrates Autopsy analysis and Mutation optimization
"""

import asyncio
import time
from jarvis_os import JarvisOS, AgentConfig


async def main():
    print("=" * 60)
    print("Jarvis-OS Example 3: Self-Improvement Loop")
    print("=" * 60)
    
    config = AgentConfig(
        name="improve-agent",
        max_workers=5,
        task_timeout=30.0,
        auto_optimize=False,  # Manual control for demo
        error_threshold=0.1,
    )
    
    agent = JarvisOS(config)
    await agent.start()
    print(f"✓ Agent started\n")
    
    # Task that sometimes fails
    async def unstable_task(item_id):
        """Task with some failures"""
        await asyncio.sleep(0.05)
        # Simulate 20% failure rate
        if item_id % 5 == 0:
            raise Exception(f"Task {item_id} failed")
        return {"id": item_id, "value": item_id * 2}
    
    # Execute tasks and collect results
    print("--- Phase 1: Executing Tasks ---")
    for i in range(10):
        try:
            result = await agent.execute_task(
                task_type="work",
                task_func=unstable_task,
                task_params={"args": [i]},
            )
            if result.result:
                print(f"✓ Task {i}: success")
        except Exception as e:
            print(f"✗ Task {i}: failed - {e}")
    
    # Analyze performance
    print("\n--- Phase 2: Analysis ---")
    analysis = agent.autopsy.analyze()
    
    print(f"Analysis results:")
    print(f"  - Total entries: {analysis.total_entries}")
    print(f"  - Error rate: {analysis.error_rate:.1%}")
    print(f"  - Avg execution time: {analysis.avg_execution_time:.4f}s")
    print(f"  - Patterns detected: {len(analysis.patterns)}")
    
    if analysis.patterns:
        print(f"\nError patterns:")
        for pattern in analysis.patterns[:3]:
            print(f"  - {pattern['error']}: {pattern['frequency']} occurrences ({pattern['percentage']:.1f}%)")
    
    if analysis.suggestions:
        print(f"\nAutonomous suggestions:")
        for suggestion in analysis.suggestions[:3]:
            print(f"  - {suggestion}")
    
    # Generate and apply mutations
    print("\n--- Phase 3: Self-Improvement ---")
    suggestions = agent.mutation.generate_suggestions({
        "error_rate": analysis.error_rate,
        "avg_execution_time": analysis.avg_execution_time,
        "patterns": analysis.patterns,
        "hotspots": analysis.hotspots,
    })
    
    print(f"Generated {len(suggestions)} improvement suggestions")
    
    # Apply high-confidence updates
    applied = 0
    for suggestion in suggestions:
        if suggestion.confidence_score >= 0.75:
            agent.mutation.apply_update(suggestion)
            applied += 1
            print(f"  ✓ Applied: {suggestion.category} "
                  f"(confidence: {suggestion.confidence_score:.1%})")
    
    print(f"\n✓ Applied {applied} improvements")
    
    # Show current instructions
    print(f"\n--- Phase 4: Updated Instructions ---")
    instructions = agent.mutation.get_current_instructions()
    for key, value in list(instructions.items())[:3]:
        print(f"  - {key}: {value}")
    
    # Show metrics
    print(f"\n--- Final Metrics ---")
    metrics = agent.get_metrics()
    print(f"Memory hit rate: {metrics['memory']['hit_rate']:.1%}")
    print(f"Mutation history: {metrics['mutations']} updates")
    
    await agent.stop()
    print(f"\n✓ Agent stopped - Self-improvement cycle complete")


if __name__ == "__main__":
    asyncio.run(main())
