"""
Example 7: Swara AI Developer Integration

This example demonstrates how an external project (like Swara AI) 
can import Jarvis-OS, register its own custom CLI tools using decorators,
and safely test generated code in the Sandbox environment.
"""

import asyncio
import logging
from jarvis_os import AgentConfig, JarvisOS
from developer_tools import jarvis_tool, SandboxManager, CLIExecutor

logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Swara AI (Powered by Jarvis-OS) ---")
    
    # 1. Swara AI boots the underlying Jarvis engine
    config = AgentConfig(name="Swara-Dev-Agent", max_workers=5)
    agent = JarvisOS(config)
    await agent.start()
    
    # Register the CLI Executor to the FastRouter so Jarvis knows how to handle CLI tasks
    agent.router.register_executor("cli_handler", CLIExecutor(max_workers=3, timeout=5.0))
    agent.router.add_route("cli_command", lambda t, p: t == "cli_command", "cli_handler")

    # 2. Swara AI registers a custom tool using the Jarvis Decorator!
    # By simply adding this decorator, this function gets wrapped in Jarvis 
    # timeouts, memory logging, and autopsy tracking.
    @jarvis_tool(agent, "file_writer")
    async def write_code_file(filepath: str, content: str):
        print(f"[Swara AI] Writing to {filepath}...")
        with open(filepath, "w") as f:
            f.write(content)
        return "File written successfully."


    # 3. Simulate Swara AI generating some Python code
    generated_code = \"\"\"
def calculate_fibonacci(n):
    if n <= 1: return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

print(calculate_fibonacci(10))
    \"\"\"
    
    # 4. Swara uses the Sandbox to safely test the generated code
    sandbox = SandboxManager(agent)
    print("\n[Swara AI] Testing generated code in Sandbox...")
    test_result = await sandbox.evaluate_code(generated_code)
    
    if test_result["success"]:
        print(f"Test Passed! Output: {test_result['stdout']}")
        
        # 5. Since it passed, Swara uses the protected tool to write it to disk
        print("\n[Swara AI] Deploying code...")
        await write_code_file("swara_fibonacci_output.py", generated_code)
    else:
        print(f"Test Failed! Error: {test_result['error']}")

    print("\nShutting down Swara and Jarvis...")
    import os
    if os.path.exists("swara_fibonacci_output.py"):
        os.remove("swara_fibonacci_output.py") # cleanup test file
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
