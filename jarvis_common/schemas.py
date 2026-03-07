from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum
import uuid
import time

class ErrorCategory(str, Enum):
    LLM_OUTPUT_MALFORMED = "LLMOutputMalformed"
    TOOL_CALL_TIMEOUT = "ToolCallTimeout"
    SANDBOX_DENIED = "SandboxPermissionDenied"
    ROUTER_MISMATCH = "RouterMisclassification"
    NETWORK_ERROR = "NetworkError"
    UNKNOWN = "UnknownError"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ExperimentStatus(str, Enum):
    RUNNING = "running"
    PROMOTED = "promoted"
    REJECTED = "rejected"

class Experiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mutation_id: str
    control_config: Dict[str, Any]
    treatment_config: Dict[str, Any]
    traffic_split: float = 0.10
    min_samples: int = 50
    metric: str = "success_rate"
    status: ExperimentStatus = ExperimentStatus.RUNNING
    
class ExperimentResult(BaseModel):
    experiment_id: str
    winner: str # "control" or "treatment"
    control_success_rate: float
    treatment_success_rate: float
    p_value: float
    samples_evaluated: int

class RouterDecision(BaseModel):
    classifier_score: float
    chosen_executor: str
    experiment_id: Optional[str] = None

class MemoryResult(BaseModel):
    key: str
    relevance_score: float

class CausalTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_input: str
    router_decision: RouterDecision
    context_retrieved: List[MemoryResult]
    prompt_length_tokens: int
    model_config: Dict[str, Any]
    llm_response_raw: str
    parse_success: bool
    error_category: Optional[ErrorCategory] = None
    outcome: TaskStatus

class CausalCluster(BaseModel):
    cluster_id: str
    error_category: ErrorCategory
    description: str
    common_features: Dict[str, Any]
    trace_ids: List[str]

class Session(BaseModel):
    session_id: str
    start_time: float = Field(default_factory=time.time)
    commands: List[str] = []
    inferred_goal: Optional[str] = None
    goal_achieved: Optional[bool] = None
    achievement_confidence: Optional[float] = None
    last_activity: float = Field(default_factory=time.time)

class DirectiveType(str, Enum):
    ROUTE_TO_CLOUD = "route_to_cloud"
    INJECT_CONTEXT = "inject_context"

class Directive(BaseModel):
    directive_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: DirectiveType
    payload: Dict[str, Any]

from datetime import datetime

class ConfidenceRecord(BaseModel):
    trace_id: str
    predicted_confidence: float
    actual_success: bool
    timestamp: datetime = Field(default_factory=datetime.now)

class CalibrationProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    temperature_scalar: float = 1.0
    brier_score: Optional[float] = None
    last_fitted_at: datetime = Field(default_factory=datetime.now)
    records_used: int

class PromptVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt_text: str
    generation: int
    parent_a_id: Optional[str] = None
    parent_b_id: Optional[str] = None
    mutations_generated: int = 0
    mutations_promoted: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def yield_rate(self) -> float:
        if self.mutations_generated == 0:
            return 0.0
        return self.mutations_promoted / self.mutations_generated
