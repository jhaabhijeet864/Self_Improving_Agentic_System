import random
import logging
from typing import Tuple, Dict, Any, List
from statsmodels.stats.proportion import proportions_ztest
from jarvis_common.schemas import Experiment, ExperimentResult, ExperimentStatus
from mutation import InstructionUpdate

logger = logging.getLogger(__name__)

class ExperimentEngine:
    """
    Phase 1: The Controlled Experiment Framework (A/B Testing Mutations)
    Wraps the FastRouter to run online statistical A/B tests on system mutations.
    """
    def __init__(self):
        self.active_experiments: Dict[str, Experiment] = {}
        # Stores results for evaluation: { experiment_id: {"control": [1, 0, 1...], "treatment": [0, 1, 1...]} }
        self.experiment_data: Dict[str, Dict[str, List[int]]] = {}

    def create_experiment(self, mutation: InstructionUpdate, control_config: Dict[str, Any]) -> Experiment:
        """
        Creates a new experiment from a proposed mutation.
        """
        experiment = Experiment(
            mutation_id=mutation.id,
            control_config=control_config,
            treatment_config=mutation.new_instruction,
            traffic_split=0.10,  # default 10%
            min_samples=50
        )
        self.active_experiments[experiment.experiment_id] = experiment
        self.experiment_data[experiment.experiment_id] = {"control": [], "treatment": []}
        logger.info(f"Created Experiment {experiment.experiment_id} for Mutation {mutation.id}")
        return experiment

    def route_with_experiment(self, query: str, active_experiment: Experiment, base_router) -> Tuple[str, bool]:
        """
        Intercepts routing decisions and probabilistically routes to the treatment path.
        Returns (executor_id, is_treatment).
        
        Note: `base_router` is passed to allow fallback if needed, but the main goal 
        is deciding which config (control vs treatment) to use for this request.
        For simplicity in routing interception, we return whether the treatment was chosen.
        The actual executor choice would depend on how the config alters the base_router.
        """
        is_treatment = random.random() < active_experiment.traffic_split
        
        # Here you would typically apply active_experiment.treatment_config 
        # to a temporary router or rule engine to get the executor_id.
        # As a simplified proxy, we'll just return the decision branch.
        
        # We assume the caller uses `is_treatment` to apply the correct config, 
        # but we also need an executor_id. In a real implementation, 
        # `treatment_config` might specify a different executor or priority.
        
        # Fake executor selection based on config
        if is_treatment:
            executor_id = active_experiment.treatment_config.get("executor_id", "treatment_executor")
        else:
            executor_id = active_experiment.control_config.get("executor_id", "control_executor")
            
        return executor_id, is_treatment

    def record_outcome(self, experiment_id: str, is_treatment: bool, success: bool):
        """
        Records the boolean outcome (1 for success, 0 for failure) of a request 
        in the experiment data.
        """
        if experiment_id not in self.experiment_data:
            return
            
        group = "treatment" if is_treatment else "control"
        self.experiment_data[experiment_id][group].append(1 if success else 0)

    def evaluate(self, experiment: Experiment) -> ExperimentResult:
        """
        Evaluates the experiment using a two-proportion z-test.
        Emits promotion/rejection events based on statistical significance.
        """
        data = self.experiment_data.get(experiment.experiment_id)
        if not data:
            raise ValueError(f"No data for experiment {experiment.experiment_id}")
            
        control_results = data["control"]
        treatment_results = data["treatment"]
        
        control_successes = sum(control_results)
        control_n = len(control_results)
        
        treatment_successes = sum(treatment_results)
        treatment_n = len(treatment_results)
        
        if treatment_n < experiment.min_samples:
            logger.info(f"Experiment {experiment.experiment_id} needs more samples ({treatment_n}/{experiment.min_samples})")
            # Not enough data, return intermediate result with p_value=1.0
            return ExperimentResult(
                experiment_id=experiment.experiment_id,
                winner="pending",
                control_success_rate=control_successes / control_n if control_n > 0 else 0.0,
                treatment_success_rate=treatment_successes / treatment_n if treatment_n > 0 else 0.0,
                p_value=1.0,
                samples_evaluated=treatment_n
            )
            
        # Run 2-proportion z-test
        count = [treatment_successes, control_successes]
        nobs = [treatment_n, control_n]
        
        stat, p_value = proportions_ztest(count, nobs, alternative='larger')
        
        # Calculate rates
        c_rate = control_successes / control_n if control_n > 0 else 0.0
        t_rate = treatment_successes / treatment_n if treatment_n > 0 else 0.0
        
        # If p < 0.05, treatment is significantly better
        if p_value < 0.05:
            winner = "treatment"
            experiment.status = ExperimentStatus.PROMOTED
            logger.info(f"Experiment {experiment.experiment_id} PROMOTED. p_value={p_value:.4f}")
        else:
            winner = "control"
            experiment.status = ExperimentStatus.REJECTED
            logger.info(f"Experiment {experiment.experiment_id} REJECTED. p_value={p_value:.4f}")
            
        return ExperimentResult(
            experiment_id=experiment.experiment_id,
            winner=winner,
            control_success_rate=c_rate,
            treatment_success_rate=t_rate,
            p_value=p_value,
            samples_evaluated=treatment_n
        )
