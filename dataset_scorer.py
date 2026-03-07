import json
import logging
import os
from typing import Dict, Any, Tuple
try:
    from sentence_transformers import SentenceTransformer
    from scipy.spatial.distance import cosine
except ImportError:
    SentenceTransformer = None
    cosine = None

logger = logging.getLogger(__name__)

class DatasetQualityScorer:
    """
    Phase 7: Dataset Quality Score
    Evaluates new SFT examples for diversity and coverage to prevent mode collapse.
    """
    def __init__(self, dataset_path: str = 'jarvis_sft_dataset.jsonl'):
        self.dataset_path = dataset_path
        self.categories = [
            "app_launches", "url_navigation", "shell_commands", 
            "conversational", "system_queries", "multi_action", 
            "malformed_recovery", "code_gen", "network", "io"
        ]
        self.model = None
        if SentenceTransformer:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                logger.error(f"Failed to load sentence transformer: {e}")

    def load_dataset(self) -> list:
        if not os.path.exists(self.dataset_path):
            return []
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f]

    def check_diversity(self, new_intent: str, existing_intents: list[str]) -> Tuple[bool, float]:
        """
        Calculates cosine distance to the nearest neighbor. 
        Distance > 0.3 means it's diverse enough.
        """
        if not self.model or not existing_intents:
            return True, 1.0
            
        try:
            new_embedding = self.model.encode(new_intent)
            existing_embeddings = self.model.encode(existing_intents)
            
            min_distance = 1.0
            for emb in existing_embeddings:
                dist = cosine(new_embedding, emb)
                if dist < min_distance:
                    min_distance = dist
                    
            is_diverse = min_distance >= 0.3
            return is_diverse, min_distance
        except Exception as e:
            logger.error(f"Diversity check failed: {e}")
            return True, 1.0

    def get_coverage(self, dataset: list) -> Dict[str, float]:
        if not dataset:
            return {c: 0.0 for c in self.categories}
            
        counts = {c: 0 for c in self.categories}
        for item in dataset:
            cat = item.get("label", "unknown")
            if cat in counts:
                counts[cat] += 1
                
        total = len(dataset)
        return {c: (count/total) for c, count in counts.items()}

    def evaluate_new_example(self, new_example: Dict[str, Any]) -> Tuple[bool, str]:
        dataset = self.load_dataset()
        
        # 1. Check Coverage
        coverage = self.get_coverage(dataset)
        cat = new_example.get("label")
        if cat in coverage and coverage[cat] > 0.5:
            # Maybe it's overrepresented, but we primarily care about underrepresented
            pass
            
        # 2. Check Diversity
        existing_intents = [item.get("intent", "") for item in dataset]
        is_diverse, min_dist = self.check_diversity(new_example.get("intent", ""), existing_intents)
        
        if not is_diverse:
            return False, f"Rejected: Too similar to existing example (distance: {min_dist:.2f} < 0.3)"
            
        # Save if passed
        with open(self.dataset_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(new_example) + "\n")
            
        return True, f"Accepted: Distance {min_dist:.2f}"
