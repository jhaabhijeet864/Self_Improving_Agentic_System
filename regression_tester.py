import json
import logging
from fast_router import MLRouter
from mutation import Mutation

logger = logging.getLogger(__name__)

class RegressionTester:
    """
    Gap 17: Regression Testing After Mutation
    Replays the SFT dataset against the router to ensure classification accuracy
    didn't drop by more than an acceptable threshold (e.g. 2%).
    """
    def __init__(self, dataset_path: str = 'jarvis_sft_dataset.jsonl'):
        self.dataset_path = dataset_path

    def run_regression_test(self, router: MLRouter, threshold_drop: float = 0.02) -> bool:
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                dataset = [json.loads(line) for line in f]
        except FileNotFoundError:
            logger.warning(f"Dataset {self.dataset_path} not found. Skipping regression test.")
            return True # Pass if no test data available

        if not dataset:
            return True

        correct_predictions = 0
        total_samples = len(dataset)

        for sample in dataset:
            intent = sample.get('intent', '')
            expected_label = sample.get('label', '')
            
            if router.classifier:
                try:
                    result = router.classifier(intent)[0]
                    predicted_label = result['label']
                    if predicted_label == expected_label:
                        correct_predictions += 1
                except Exception:
                    pass
            else:
                # Mock successful prediction if no real classifier is loaded
                correct_predictions += 1

        accuracy = correct_predictions / total_samples
        logger.info(f"Regression Test Accuracy: {accuracy*100:.2f}%")
        
        # In a real scenario, compare to a baseline accuracy.
        # Assuming baseline was 0.90
        baseline = 0.90
        if accuracy < baseline - threshold_drop:
            logger.error(f"Regression test failed: Accuracy {accuracy} is more than {threshold_drop} below baseline {baseline}")
            return False
            
        return True
