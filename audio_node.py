"""
Multimodal Audio Node - Continuous Hearing and Speaking
Hooks into Jarvis-OS for continuous AI interaction via STT (Speech-to-Text) 
and TTS (Text-to-Speech).
"""

import asyncio
import time
import logging
from typing import Callable, Any, Optional

from jarvis_os import JarvisOS

logger = logging.getLogger(__name__)

class AudioNode:
    """
    Continuous audio processing node for Jarvis-OS.
    Listens for speech, converts it to text, routes it to the agent,
    and speaks the agent's textual response back out.
    """
    def __init__(
        self, 
        agent: JarvisOS,
        stt_engine: Optional[Callable[[bytes], str]] = None,
        tts_engine: Optional[Callable[[str], bytes]] = None,
        vad_threshold: float = 0.5
    ):
        """
        Initialize Audio Node.
        
        Args:
            agent: The Jarvis-OS instance to route text to.
            stt_engine: Function converting audio bytes to text string (e.g., Whisper).
            tts_engine: Function converting text string to audio bytes (e.g., ElevenLabs).
            vad_threshold: Voice Activity Detection sensitivity threshold.
        """
        self.agent = agent
        self.stt_engine = stt_engine or self._mock_stt
        self.tts_engine = tts_engine or self._mock_tts
        self.vad_threshold = vad_threshold
        self.is_listening = False
        
    def _mock_stt(self, audio_data: bytes) -> str:
        """Mock Speech-to-Text for development"""
        logger.info("[Mock STT] Transcribing audio block...")
        time.sleep(0.5)
        return "this is a mock transcription"
        
    def _mock_tts(self, text: str) -> bytes:
        """Mock Text-to-Speech for development"""
        logger.info(f"[Mock TTS] Synthesizing speech for: '{text}'")
        time.sleep(0.5)
        return b"mock_audio_data"

    async def _audio_in_task(self, audio_data: bytes) -> str:
        """Execute STT wrapped in Jarvis protections"""
        return await asyncio.to_thread(self.stt_engine, audio_data)
        
    async def _audio_out_task(self, text: str) -> bool:
        """Execute TTS and playback wrapped in Jarvis protections"""
        try:
            audio_bytes = await asyncio.to_thread(self.tts_engine, text)
            # Example: In a real app we would play `audio_bytes` using pyaudio/sounddevice
            logger.info(f"[AudioOut] Playing {len(audio_bytes)} bytes of audio.")
            return True
        except Exception as e:
            logger.error(f"Audio Out failed: {e}")
            return False

    async def start_listening_loop(self, process_callback: Callable[[str], str]):
        """
        Start the continuous audio capture loop.
        
        Args:
            process_callback: Async function that takes the transcribed text
                              as input, queries the AI, and returns the AI's response text.
        """
        self.is_listening = True
        logger.info("🎙️ Audio Node Listening Loop Started...")
        
        while self.is_listening:
            try:
                # 1. Capture Audio (In a real app, this blocks until VAD detects speech)
                # Here we simulate periodic speech detection.
                await asyncio.sleep(5.0) 
                simulated_audio = b"sim_audio_capture"
                
                # 2. Route STT Task to Jarvis-OS
                # Autopsy will track the duration of STT transcribing
                stt_result = await self.agent.execute_task(
                    task_type="audio_in_stt",
                    task_func=self._audio_in_task,
                    task_params={"args": [simulated_audio]}
                )
                
                if stt_result.status.value != "completed":
                    continue
                    
                transcription = stt_result.result
                logger.info(f"🗣️ User Said: '{transcription}'")
                
                # 3. Process transcription with AI Brain
                ai_response = await process_callback(transcription)
                logger.info(f"🤖 Brain Output: '{ai_response}'")
                
                # 4. Route TTS Task to Jarvis-OS
                # Autopsy tracks voice synthesis latency
                tts_result = await self.agent.execute_task(
                    task_type="audio_out_tts",
                    task_func=self._audio_out_task,
                    task_params={"args": [ai_response]}
                )
                
            except Exception as e:
                logger.error(f"Audio loop error: {e}")
                
    def stop(self):
        """Stop listening"""
        self.is_listening = False
        logger.info("Audio Node stopped.")
