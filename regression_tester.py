"""
Jarvis OS Automated Regression Tester
Validates that new AI-generated mutations don't silently break core SFT behaviors
by executing a suite of offline regression checks.
"""

import json
import logging
import os
from ml_router import MLRouter
from fast_router import TaskPriority

logger = logging.getLogger(__name__)

class RegressionTester:
    def __init__(self, dataset_path="jarvis_sft_dataset.jsonl"):
        self.dataset_path = dataset_path
        self.router = MLRouter()
        
    def _load_dataset(self):
        """Load JSONL testing rows."""
        dataset = []
        if not os.path.exists(self.dataset_path):
            logger.warning(f"SFT Dataset {self.dataset_path} not found. Running with baseline tests.")
            return [
                {"input": "Start a local server on port 3000", "expected_executor": "cli_handler"},
                {"input": "What is the square root of 994?", "expected_executor": "high_priority"},
                {"input": "Read configuration from config.txt", "expected_executor": "background_io"},
            ]
            
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
        return dataset
        
    def run_routing_regression(self) -> float:
        """
        Tests the ML Router against historical baseline truth.
        Returns percentage accuracy 0.0 to 1.0.
        """
        logger.info("Initializing SFT Routing Regression Suite...")
        dataset = self._load_dataset()
        
        if not dataset:
            return 1.0
            
        correct = 0
        total = len(dataset)
        
        for case in dataset:
            # Simulate routing
            executor, priority = self.router.route_task(
                task_type="test",
                task_params={"description": case["input"]},
                priority=TaskPriority.NORMAL
            )
            
            if executor == case["expected_executor"]:
                correct += 1
            else:
                logger.error(f"Regression FAIL: '{case['input']}' routed to '{executor}' (Expected '{case['expected_executor']}')")
                
        accuracy = correct / total
        logger.info(f"Regression Suite Complete. Accuracy: {accuracy*100:.2f}% ({correct}/{total})")
        
        return accuracy
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tester = RegressionTester()
    acc = tester.run_routing_regression()
    if acc < 0.95:
        logger.warning("WARNING: Regression Accuracy fell below the 95% Tier-1 SLA threshold.")
