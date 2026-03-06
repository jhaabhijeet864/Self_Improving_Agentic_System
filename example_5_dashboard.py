"""
Example 5: Jarvis-OS with Real-Time Data Dashboard

This example demonstrates how to launch a Jarvis-OS agent while
simultaneously serving its real-time telemetry through a web interface.

Note: You must have `fastapi` and `uvicorn` installed.
"""

import asyncio
from jarvis_os import AgentConfig, JarvisOS
from dashboard import JarvisDashboard
import random

async def bg_task_generator(agent: JarvisOS):
    """Simulate random background tasks generating metrics over time"""
    async def mock_compute(value):
        await asyncio.sleep(random.uniform(0.1, 0.5))
        if random.random() < 0.1:  # 10% chance of failure
            raise ValueError("Random simulated failure")
        return value * 2

    while True:
        try:
            # Dispatch 3 random tasks concurrently
            await asyncio.gather(
                agent.execute_task("sim", mock_compute, {"args": [random.randint(1, 100)]}),
                agent.execute_task("sim", mock_compute, {"args": [random.randint(1, 100)]}),
                agent.execute_task("sim", mock_compute, {"args": [random.randint(1, 100)]}, persistent_memory=True),
            )
        except Exception:
            pass # ignore expected mock failures
            
        await asyncio.sleep(2) # Generate new tasks every 2 seconds

async def main():
    print("--- Jarvis-OS Web Dashboard Example ---")
    
    # 1. Initialize Agent
    config = AgentConfig(name="WebDashboard-Agent", max_workers=10)
    agent = JarvisOS(config)
    await agent.start()
    
    try:
        # 2. Start the FastAPI Dashboard
        dashboard = JarvisDashboard(agent, port=8000)
        
        # 3. Start generating dummy tasks in the background
        generator_task = asyncio.create_task(bg_task_generator(agent))
        
        # 4. Serve the dashboard application (blocking)
        print("\n[!] Dashboard Live: Open http://localhost:8000 in your browser.")
        print("[!] Press Ctrl+C to stop.")
        
        await dashboard.serve_async()
        
    except ImportError:
        print("\n[Skipping] `fastapi` or `uvicorn` is not installed.")
        print("Run: pip install fastapi uvicorn")
        
    finally:
        print("\nShutting down agent...")
        generator_task.cancel()
        await agent.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
