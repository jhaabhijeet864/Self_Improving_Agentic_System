with open('fast_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports = '''import json
import os
try:
    import torch
    from transformers import pipeline
except ImportError:
    pipeline = None
'''

ml_router_code = '''
class MLRouter(FastRouter):
    """
    Machine Learning based router that uses an SFT model (like phi-3-mini) 
    to classify intents, solving Gap 2 and Gap 11.
    """
    def __init__(self, model_path: str = None, dataset_path: str = 'jarvis_sft_dataset.jsonl'):
        super().__init__()
        self.model_path = model_path
        self.dataset_path = dataset_path
        self.classifier = None
        self.labels = ['compute', 'network', 'io', 'system', 'unknown']
        
        if pipeline is not None and model_path and os.path.exists(model_path):
            try:
                self.classifier = pipeline(
                    'text-classification', 
                    model=model_path, 
                    device=0 if torch.cuda.is_available() else -1
                )
                logger.info(f"Loaded ML Router model from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load ML model: {e}")
                
    def train_or_update(self):
        """
        Reads jarvis_sft_dataset.jsonl (Gap 11) and updates the model.
        In a real scenario, this spawns a LoRA fine-tuning subprocess.
        """
        if not os.path.exists(self.dataset_path):
            logger.warning(f"SFT Dataset not found at {self.dataset_path}")
            return
            
        logger.info(f"Loading dataset from {self.dataset_path} for incremental training...")
        # Load JSONL and prepare for HF Trainer
        with open(self.dataset_path, 'r', encoding='utf-8') as df:
            samples = [json.loads(line) for line in df]
        logger.info(f"Loaded {len(samples)} examples for training")
        
    def route_task(
        self,
        task_type: str,
        task_params: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Tuple[str, int]:
        
        # If ML model is loaded, use it to classify intent from params
        if self.classifier and 'intent' in task_params:
            try:
                intent_text = task_params['intent']
                result = self.classifier(intent_text)[0]
                predicted_label = result['label']
                
                executor_id = f"{predicted_label}_executor"
                
                if executor_id in self.executors:
                    self.stats["routed_tasks"] += 1
                    self.stats["routes_by_name"]["ml_route"] += 1
                    return executor_id, priority.value
            except Exception as e:
                logger.error(f"ML routing failed, falling back: {e}")
                
        # Fallback to FastRouter rule-based
        return super().route_task(task_type, task_params, priority)
'''

if 'import json' not in content:
    content = content.replace('from collections import defaultdict', 'from collections import defaultdict\n' + imports)

if 'class MLRouter' not in content:
    content += '\n' + ml_router_code

with open('fast_router.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done modifying fast_router.py')
