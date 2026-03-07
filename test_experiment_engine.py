import random
import logging
from experiment_engine import ExperimentEngine
from jarvis_common.schemas import ExperimentStatus
from mutation import InstructionUpdate

logging.basicConfig(level=logging.INFO)

def test_experiment_engine():
    engine = ExperimentEngine()
    
    # Mock mutation
    mutation = InstructionUpdate(
        id="mut-123",
        timestamp=1.0,
        category="routing",
        priority="high",
        description="Test mutation",
        old_instruction={"executor_id": "old"},
        new_instruction={"executor_id": "new"},
        reasoning="Test",
        confidence_score=0.9
    )
    
    experiment = engine.create_experiment(mutation, control_config={"executor_id": "old"})
    # Override split for test
    experiment.traffic_split = 0.50
    
    # Simulate 1000 requests to get enough samples for statistical significance
    # Control success rate: 50%
    # Treatment success rate: 70% (+20%)
    for _ in range(1000):
        executor_id, is_treatment = engine.route_with_experiment("dummy query", experiment, None)
        
        if is_treatment:
            success = random.random() < 0.70
        else:
            success = random.random() < 0.50
            
        engine.record_outcome(experiment.experiment_id, is_treatment, success)
        
    result = engine.evaluate(experiment)
    
    print(f"\\n--- Test Results ---")
    print(f"Winner: {result.winner}")
    print(f"Control Rate: {result.control_success_rate:.2f}")
    print(f"Treatment Rate: {result.treatment_success_rate:.2f}")
    print(f"P-Value: {result.p_value:.4f}")
    
    assert result.winner == "treatment", "Treatment should win"
    assert result.p_value < 0.05, "P-value should be significant"
    assert experiment.status == ExperimentStatus.PROMOTED, "Experiment should be promoted"
    print("Test passed! Phase 1 DoD met.\\n")

if __name__ == "__main__":
    test_experiment_engine()
