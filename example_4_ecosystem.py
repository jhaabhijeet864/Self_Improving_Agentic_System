"""
Example 4: Using Ecosystem Wrappers with Jarvis-OS

This example demonstrates how to use the custom LangChain and LlamaIndex
executors to run external framework pipelines with Jarvis-OS protections
(timeouts, concurrency limits, and tracking).

Note: You must have `langchain` and `llama_index` installed to run this script.
"""

import asyncio
from ecosystem_executors import LangChainExecutor, LlamaIndexExecutor
from jarvis_os import AgentConfig, JarvisOS
import time

async def main():
    print("--- Jarvis-OS Ecosystem Integration Example ---")
    
    # 1. Initialize Jarvis-OS as usual
    config = AgentConfig(
        name="ecosystem-agent",
        max_workers=5
    )
    agent = JarvisOS(config)
    await agent.start()
    
    # 2. Setup standard LLM frameworks
    try:
        from langchain.prompts import PromptTemplate
        from langchain.schema.runnable import RunnableLambda
        
        # A mock LangChain runnable
        def mock_llm_call(prompt: str) -> str:
            time.sleep(1) # simulate network call
            return f"[LangChain Output]: Processed '{prompt}'"
            
        chain = PromptTemplate.from_template("Hello {name}") | RunnableLambda(mock_llm_call)
        
        # 3. Create our custom executor
        lc_executor = LangChainExecutor(max_workers=3, timeout=10.0)
        
        # 4. Route task execution through the ecosystem wrapper
        print("\nExecuting LangChain Chain...")
        result = await lc_executor.execute_chain(chain, {"name": "Jarvis"})
        print(f"Status: {result.status.value}")
        print(f"Result: {result.result}")
        print(f"Time: {result.execution_time:.2f}s")
        
    except ImportError:
        print("\n[Skipping LangChain] LangChain is not installed.")

    print("\nShutting down...")
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
