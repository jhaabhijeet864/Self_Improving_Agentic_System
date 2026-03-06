"""
Example 6: Multimodal Autonomous Agents (Vision & Audio)

This example demonstrates how to boot Jarvis-OS with continuous
"Hearing" and "Seeing" capabilities running in the background.
"""

import asyncio
import logging
from jarvis_os import AgentConfig, JarvisOS
from audio_node import AudioNode
from vision_node import VisionNode

logging.basicConfig(level=logging.INFO)

async def main():
    print("--- Jarvis-OS Multimodal Setup ---")
    
    # 1. Initialize Core Agent
    config = AgentConfig(name="Multimodal-Agent", max_workers=10)
    agent = JarvisOS(config)
    await agent.start()
    
    # 2. Define the Brain reaction logic
    async def process_voice_input(transcription: str) -> str:
        """Callback fired every time the Audio Node hears speech."""
        # Here we could pass 'transcription' to an LLM chain
        agent.logger.info(f"[Brain] Processing user speech: {transcription}")
        await asyncio.sleep(0.5)
        # Store what we heard in Jarvis short-term memory
        agent.memory.store(f"user_said_{int(asyncio.get_event_loop().time())}", transcription)
        
        return f"I heard you say: {transcription}. I am processing your request."
        
    async def process_visual_change(scene_desc: str):
        """Callback fired every time the Vision Node detects movement."""
        # Store what we saw in memory so the Brain knows what's happening
        agent.logger.info(f"[Brain] Noticed a visual change: {scene_desc}")
        agent.memory.store("current_visual_context", scene_desc)
    
    # 3. Mount Sensors
    # These mount directly to Jarvis-OS to use its Executor/Router layers
    ears = AudioNode(agent)
    eyes = VisionNode(agent, change_threshold=0.10)
    
    try:
        # Start sensory loops concurrently
        print("\n[!] Starting senses... (Simulated Loops)")
        await asyncio.gather(
            ears.start_listening_loop(process_voice_input),
            eyes.start_watching_loop(process_visual_change),
            # Let it run for 20 seconds then shut down
            asyncio.sleep(20)
        )
    finally:
        print("\nShutting down senses and agent...")
        ears.stop()
        eyes.stop()
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
