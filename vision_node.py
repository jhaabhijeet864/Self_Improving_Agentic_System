"""
Multimodal Vision Node - Continuous Sight
Injects "eyes" into Jarvis-OS. Captures webcam or screen frames, uses basic computer 
vision to detect pixel differences, and only dispatches full VLM (Vision-Language Model)
analysis tasks when significant movement occurs.
"""

import asyncio
import time
import logging
from typing import Callable, Any, Optional

from jarvis_os import JarvisOS

logger = logging.getLogger(__name__)

class VisionNode:
    """
    Continuous vision processing node for Jarvis-OS.
    Captures frames, computes change, and tasks a VLM when needed.
    """
    def __init__(
        self,
        agent: JarvisOS,
        vlm_engine: Optional[Callable[[bytes], str]] = None,
        change_threshold: float = 0.15,
        capture_fps: float = 2.0
    ):
        """
        Initialize Vision Node.
        
        Args:
            agent: The Jarvis-OS instance to route visual tasks to.
            vlm_engine: Function converting image bytes to a scene description text.
            change_threshold: % of pixels that must change to trigger a VLM analysis (0.0 to 1.0).
            capture_fps: How many frames per second to capture and compare.
        """
        self.agent = agent
        self.vlm_engine = vlm_engine or self._mock_vlm
        self.change_threshold = change_threshold
        self.capture_delay = 1.0 / capture_fps
        self.is_watching = False
        self.last_frame: Optional[bytes] = None
        
    def _mock_vlm(self, image_data: bytes) -> str:
        """Mock Vision-Language Model for development"""
        logger.info("[Mock VLM] Analyzing image structure...")
        time.sleep(1.0)
        return "A person sitting at a desk looking at code."

    def _compute_frame_difference(self, frame_a: bytes, frame_b: bytes) -> float:
        """
        Compute the percentage of difference between two frames.
        In a real app, use cv2.absdiff and cv2.countNonZero.
        This is a mock implementation.
        """
        if frame_a == frame_b:
            return 0.0
        # Mock variance depending on time
        return 0.20 # simulate 20% change

    async def _vision_analysis_task(self, image_data: bytes) -> str:
        """Execute VLM wrapped in Jarvis protections"""
        return await asyncio.to_thread(self.vlm_engine, image_data)

    async def start_watching_loop(self, on_scene_change: Callable[[str], None]):
        """
        Start the continuous visual frame capture loop.
        
        Args:
            on_scene_change: Async function called with the text description of the scene
                             when significant visual changes are detected.
        """
        self.is_watching = True
        logger.info("👁️ Vision Node Watching Loop Started...")
        
        while self.is_watching:
            try:
                # 1. Capture Frame (Mocking cv2.VideoCapture.read)
                await asyncio.sleep(self.capture_delay)
                
                # Mock a frame buffer change every 10 iterations to trigger the threshold
                simulated_frame = b"static_scene" if int(time.time()) % 15 != 0 else b"dynamic_scene"
                
                # 2. Change Detection (Lightweight OpenCV comparison)
                if self.last_frame is not None:
                    diff_score = self._compute_frame_difference(self.last_frame, simulated_frame)
                    
                    if diff_score >= self.change_threshold:
                        logger.info(f"👀 Visual movement detected ({diff_score*100:.1f}% change). Routing to VLM...")
                        
                        # 3. Route Heavy VLM Task to Jarvis-OS
                        vlm_result = await self.agent.execute_task(
                            task_type="vision_in_vlm",
                            task_func=self._vision_analysis_task,
                            task_params={"args": [simulated_frame]}
                        )
                        
                        if vlm_result.status.value == "completed":
                            scene_description = vlm_result.result
                            logger.info(f"🖼️ Scene Analysis: '{scene_description}'")
                            
                            # 4. Fire callback to brain/memory
                            await on_scene_change(scene_description)
                
                # Update frame buffer
                self.last_frame = simulated_frame
                
            except Exception as e:
                logger.error(f"Vision loop error: {e}")
                
    def stop(self):
        """Stop watching"""
        self.is_watching = False
        logger.info("Vision Node stopped.")
