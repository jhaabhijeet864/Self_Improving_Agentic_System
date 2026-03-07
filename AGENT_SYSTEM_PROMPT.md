# Jarvis-OS Agent System Prompt
## The Authoritative Guide for All AI Assistants

**Version**: 2.0.0 (7-Phase Implementation)  
**Last Updated**: 2026-03-07  
**Status**: Active Development - Phases 1-3 Ready to Implement

---

## 🎯 Mission Statement

Jarvis-OS is a **self-improving AI agent framework** that learns from its mistakes, experiments safely with improvements, and builds a personalized understanding of the user's projects and workflows over time. This system is designed to be:

- **Autonomous yet supervised**: Mutations require human approval, but experiments run automatically with statistical backing
- **Transparent and auditable**: Every decision is traced and explainable
- **Continuously learning**: From error patterns, user workflows, and A/B test outcomes
- **Safe to deploy**: Automatic rollback of degrading mutations, circuit breakers for failing components

---

## 👥 Agent Personas and Capabilities

### For GitHub Copilot
**Strengths**: Code navigation, refactoring, IDE integration  
**Best for**: Implementing core modules, schema definitions, test writing  
**Prompt style**: Concise, references to existing patterns, expects full file edits

### For Claude (Code/API)
**Strengths**: Long-context reasoning, architecture, complex logic  
**Best for**: Designing the flow, explaining tradeoffs, integration points  
**Prompt style**: Detailed context, ask for design docs first, then implementation

### For Gemini (CLI/API)
**Strengths**: Speed, parallel processing, API integration  
**Best for**: Database schema design, batching operations, performance tuning  
**Prompt style**: Task-oriented, focus on throughput, API compatibility

### For Cursor/IDEs
**Strengths**: File context, multi-file editing, refactoring tools  
**Best for**: Integration work, multi-component changes  
**Prompt style**: File paths, line numbers, before/after context

**Core Directives for ALL Agents:**
1.  **Do not use dummy code or `pass` blocks** for core logic unless explicitly instructed to scaffold. 
2.  **Maintain strict separation of concerns**: Router logic stays in routers, executor logic in executors, statistical logic in engines.
3.  **Use provided schemas**: Always adhere to the Pydantic models defined in `jarvis_common/schemas.py`.

---

## 📋 Project Context & Architecture Knowledge

The self-improver sits alongside the Jarvis voice agent. The two communicate via a local WebSocket IPC bridge (`jarvis_common/events.py`). The improver analyzes Jarvis's event stream, uses an LLM to critique failures, and proposes updates (`InstructionUpdate`). Instead of blindly applying them, it runs statistical **A/B Tests**. It traces causality, tracks overarching user session goals, and actively injects directives (like forcing cloud fallback or inserting ChromaDB context) back into Jarvis in real-time.

### Key Existing Components:
*   `fast_router.py`: Handles intent routing via ML models (`phi-3-mini`).
*   `executor.py`: Sandboxed execution engine with a Circuit Breaker for latency limits.
*   `memory_manager.py`: Two-tier memory + ChromaDB semantic vector store.
*   `mutation.py`: Proposes changes to agent instructions.
*   `database.py`: SQLite persistence layer (`aiosqlite`).

---

## 3. The Shared Contract (Pydantic Schemas)
All agents must use these schemas when implementing the features below. These should be placed in `jarvis_common/schemas.py`.

```python
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
```

---

## 4. Implementation Sprint (Phases 1 - 7)

### Phase 1: The Controlled Experiment Framework (A/B Testing)
*   **Objective**: Replace binary human approvals with statistical online evaluation using a multi-armed bandit style traffic split.
*   **Implementation**: Create `experiment_engine.py`. Wrap the `FastRouter` to probabilistically divert `traffic_split` requests to the treatment rule. After `min_samples`, use `scipy.stats.proportions_ztest` to compare success rates. Emit promotion/rejection events based on $p < 0.05$.
*   **Definition of Done (DoD)**: `experiment_engine.py` exists.
*   **Test Spec**: Simulate 100 requests (50/50 split). Inject a treatment with a 20% higher success rate. Assert `ExperimentResult.winner == "treatment"` and `p_value < 0.05`.

### Phase 2: Causal Tracing
*   **Objective**: Move from symptom-logging to root-cause diagnosis.
*   **Implementation**: Plumb `trace_id` through the executor and memory managers. Output complete `CausalTrace` objects. Add `find_causal_clusters()` to Autopsy, clustering failures by executor, prompt length (>2000), and intent.
*   **DoD**: Logs contain full causal chains.
*   **Test Spec**: Generate 10 failed traces where `prompt_length_tokens > 2000` and `executor == "local"`. `find_causal_clusters` must group these into a single `CausalCluster` with a description explicitly naming those two features.

### Phase 3: Session Goal Tracking
*   **Objective**: Evaluate success on multi-step overarching user goals, not just per-command success.
*   **Implementation**: Create `session_tracker.py`. Group events by `session_id`. Every 5 commands, use an LLM call to infer the session goal. On session timeout (60s inactivity), make a final LLM call to determine if the inferred goal was achieved. Update DB.
*   **DoD**: System writes session goals and boolean achievements to SQLite.
*   **Test Spec**: Feed a mock stream of 6 commands relating to building a FastAPI app. Assert the tracker sets an `inferred_goal` containing "FastAPI" and evaluates `goal_achieved`.

### Phase 4: Real-Time Guidance Injection (Bidirectional IPC)
*   **Objective**: Transform the self-improver into an active co-pilot.
*   **Implementation**: Make `ipc_server.py` capable of sending messages. Create a listener in the main Jarvis loop. Support `RouteToCloudDirective` (trips circuit breaker) and `InjectContextDirective`.
*   **DoD**: The improver can trigger state changes in the executing Jarvis instance within a 50ms latency window.
*   **Test Spec**: Fire a `RouteToCloudDirective` over IPC. Assert the next simulated task strictly routes to the cloud executor, bypassing local.

### Phase 5: Project Context Graph
*   **Objective**: Persistent, semantic memory of user projects to pre-warm the LLM context window.
*   **Implementation**: Extend ChromaDB logic. On session success (Phase 3), embed the command sequence and inferred goal into ChromaDB as a "Project Snapshot". On new session start, semantic query ChromaDB using the first 3 commands and inject via Phase 4 IPC.
*   **DoD**: Context injection occurs automatically based on past successful sessions.
*   **Test Spec**: Store a "React Bugfix" snapshot. Start a new session with "npm run start debugging". Assert ChromaDB returns the React snapshot and fires an `InjectContextDirective`.

### Phase 6: Mutation Impact Report & Rollback Budget
*   **Objective**: Automated safety nets and reporting for unattended mutations.
*   **Implementation**: Background async task runs every 30 minutes. Compares trailing 24h success/goal-achievement rates to pre-mutation baselines. If metrics drop > 5% with 95% confidence, trigger snapshot rollback. Generate Markdown reports in `mutations/impact_reports/`.
*   **DoD**: `impact_{mutation_id}.md` is written. System auto-reverts bad changes.
*   **Test Spec**: Mock a database with 500 successes pre-mutation, and 400 failures post-mutation. Trigger the background job; assert it fires a rollback event and writes the MD report.

### Phase 7: Dataset Quality Score
*   **Objective**: Prevent mode collapse in SFT fine-tuning data (`jarvis_sft_dataset.jsonl`).
*   **Implementation**: Create `DatasetQualityScorer`. When appending new data, check Diversity (cosine distance to nearest neighbor using `sentence-transformers` > 0.3) and Coverage (ensure all 10 scenario categories maintain > 5% share).
*   **DoD**: High-quality SFT gating. Expose scores to the Dashboard UI.
*   **Test Spec**: Submit a duplicate SFT example. Assert it is rejected (distance < 0.3). Submit an example in an underrepresented category; assert it is added and the distribution graph data updates.

---

## 5. Complete Phase Specifications

### Phase 1: Controlled Experiment Framework (A/B Testing Mutations)
**Status**: READY TO IMPLEMENT | **Effort**: 40-60 hours | **Criticality**: HIGHEST

#### Philosophy
Mutations are no longer binary (approve/reject). Instead, propose a change, run a statistical experiment where 10% of traffic uses the new rule and 90% uses the old, then let math decide the winner. This is the core of the self-improvement loop.

#### Pydantic Models (add to `jarvis_common/schemas.py`)
```python
class ExperimentStatus(str, Enum):
    RUNNING = "running"
    PROMOTED = "promoted"
    REJECTED = "rejected"

class Experiment(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mutation_id: str
    control_config: Dict[str, Any]  # Current routing rules
    treatment_config: Dict[str, Any]  # Proposed rules from mutation
    traffic_split: float = 0.10  # % of traffic to treatment
    min_samples: int = 50  # Minimum samples before evaluation
    metric: str = "success_rate"  # What to measure
    status: ExperimentStatus = ExperimentStatus.RUNNING
    started_at: datetime = Field(default_factory=datetime.now)
    evaluated_at: Optional[datetime] = None

class ExperimentResult(BaseModel):
    experiment_id: str
    winner: str  # "control", "treatment", or "tie"
    control_success_rate: float
    treatment_success_rate: float
    control_samples: int
    treatment_samples: int
    p_value: float
    effect_size: float  # (treatment - control) success rate
    confidence_interval: Tuple[float, float]  # 95% CI on effect size
```

#### Files to Implement
1. **`experiment_engine.py`** (400-500 lines)
   - `ExperimentEngine.create_experiment()`: Create new A/B test
   - `ExperimentEngine.route_with_experiment()`: Randomly split traffic
   - `ExperimentEngine.record_outcome()`: Log success/failure
   - `ExperimentEngine.evaluate()`: Run scipy.stats.proportions_ztest

2. **Modify `fast_router.py`**
   - Add `route_with_config()` method to accept explicit config

3. **Modify `structured_logger.py`**
   - Track experiment_id on every log entry
   - Allows grouping by treatment/control post-hoc

#### Database Schema
```sql
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    mutation_id TEXT UNIQUE NOT NULL,
    traffic_split REAL DEFAULT 0.10,
    min_samples INTEGER DEFAULT 50,
    status TEXT DEFAULT 'running',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP
);

CREATE TABLE experiment_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    is_treatment BOOLEAN NOT NULL,
    task_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);

CREATE TABLE experiment_results (
    experiment_id TEXT PRIMARY KEY,
    winner TEXT NOT NULL,  -- control|treatment|tie
    p_value REAL NOT NULL,
    control_rate REAL NOT NULL,
    treatment_rate REAL NOT NULL,
    effect_size REAL NOT NULL,
    FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
);
```

#### Test Specification
```python
# core test: 100 samples (50/50), treatment 20% better → detected as winner
@pytest.mark.asyncio
async def test_experiment_statistical_significance():
    engine = ExperimentEngine(mock_router, mock_db)
    exp = await engine.create_experiment(mutation, traffic_split=0.5, min_samples=50)
    
    # 50 control: 20 successes (40%)
    # 50 treatment: 30 successes (60%)
    for i in range(50):
        await engine.record_outcome(exp.experiment_id, is_treatment=False, success=i < 20)
        await engine.record_outcome(exp.experiment_id, is_treatment=True, success=i < 30)
    
    result = await engine.evaluate(exp)
    
    assert result.winner == "treatment"
    assert result.p_value < 0.05
    assert result.effect_size == 0.20
```

#### Definition of Done
- [ ] experiment_engine.py compiles
- [ ] scipy.stats.proportions_ztest correctly imported and used
- [ ] Database tables created
- [ ] Test passes (p < 0.05 when treatment is 20% better)
- [ ] Experiment outcomes logged with trace_id and experiment_id
- [ ] Dashboard shows active experiments and results
- [ ] No regression in existing router performance

---

### Phase 2: Causal Tracing
**Status**: READY TO IMPLEMENT | **Effort**: 35-50 hours | **Criticality**: HIGH

#### Philosophy
Logs currently capture "what failed" but not "why". Causal tracing propagates a `trace_id` through every component of the pipeline so we can answer: "All failures of type X happened when Y was true and Z was true."

#### Pydantic Models
```python
class ErrorCategory(str, Enum):
    LLM_OUTPUT_MALFORMED = "llm_malformed"
    TOOL_TIMEOUT = "tool_timeout"
    SANDBOX_DENIED = "sandbox_denied"
    ROUTER_MISMATCH = "router_mismatch"
    NETWORK_ERROR = "network_error"
    MEMORY_MISS = "memory_miss"
    UNKNOWN = "unknown"

class RouterDecision(BaseModel):
    chosen_executor: str
    confidence: float
    experiment_id: Optional[str] = None

class MemoryRetrieved(BaseModel):
    query: str
    retrieved_count: int
    avg_similarity: float

class CausalTrace(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_input: str
    user_input_tokens: int
    
    router_decision: RouterDecision
    experiment_id: Optional[str] = None
    
    context_retrieved: Optional[MemoryRetrieved] = None
    context_retrieval_time_ms: float
    
    prompt_full: str  # Full prompt sent to LLM
    prompt_tokens: int
    model: str  # gemini-1.5-pro, claude-3-5-sonnet, etc.
    temperature: float
    
    llm_response: str
    llm_response_tokens: int
    
    parse_success: bool
    error_category: Optional[ErrorCategory] = None
    
    outcome: str  # success|failed
    execution_time_ms: float
    created_at: datetime = Field(default_factory=datetime.now)

class CausalCluster(BaseModel):
    cluster_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    error_category: ErrorCategory
    trace_count: int
    conditions: Dict[str, Any]  # e.g., {"executor": "local", "prompt_tokens_gt": 2000}
    success_rate: float
    common_pattern: str  # Human-readable pattern description
    recommendation: str  # What to try next
```

#### Files to Implement
1. **`causal_tracer.py`** (300-400 lines)
   - `start_trace()`: Allocate trace_id
   - `record_router_decision()`: Update with routing info
   - `record_memory_retrieval()`: Update with memory info
   - `record_prompt()`: LLM details
   - `record_outcome()`: Final result
   - `find_causal_clusters()`: Group failures by conditions

2. **Modify `structured_logger.py`**
   - Every log entry includes trace_id
   - All async operations accept trace_id parameter

3. **Modify `executor.py`**
   - Pass trace_id to all subprocess calls
   - Log execution time to trace

#### Database Schema
```sql
CREATE TABLE causal_traces (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_input TEXT,
    user_input_tokens INTEGER,
    
    router_executor TEXT,
    router_confidence REAL,
    router_experiment_id TEXT,
    
    context_query TEXT,
    context_retrieved_count INTEGER,
    context_retrieval_ms REAL,
    
    prompt_text TEXT,
    prompt_tokens INTEGER,
    model_used TEXT,
    temperature REAL,
    
    llm_response TEXT,
    llm_response_tokens INTEGER,
    
    parse_success BOOLEAN,
    error_category TEXT,
    
    outcome TEXT,  -- success|failed
    execution_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX idx_traces_session ON causal_traces(session_id);
CREATE INDEX idx_traces_error_category ON causal_traces(error_category);
CREATE INDEX idx_traces_executor ON causal_traces(router_executor);
```

#### Test Specification
```python
# Test: Clustering identifies prompt length > 2000 as common factor in failures
@pytest.mark.asyncio
async def test_causal_clustering():
    tracer = CausalTracer(mock_db)
    
    # Create 10 traces: local executor, long prompt (>2000 tokens), all failed
    for i in range(10):
        trace_id = await tracer.start_trace("session-1", "test")
        await tracer.record_router_decision(trace_id, "local", 0.9)
        await tracer.record_prompt(trace_id, "x" * 10000, 2500, {"temperature": 0.3})
        await tracer.record_outcome(trace_id, "", False, ErrorCategory.LLM_OUTPUT_MALFORMED, "failed", 1000)
    
    clusters = await tracer.find_causal_clusters(ErrorCategory.LLM_OUTPUT_MALFORMED)
    
    local_long_cluster = [c for c in clusters 
        if c.conditions.get("executor") == "local" 
        and c.conditions.get("prompt_tokens_gt_2000")][0]
    
    assert local_long_cluster.trace_count == 10
    assert "prompt" in local_long_cluster.common_pattern.lower()
```

#### Definition of Done
- [ ] CausalTrace schema fully implemented
- [ ] trace_id flows through all components
- [ ] Clustering algorithm groups by 2+ conditions
- [ ] Test passes
- [ ] Dashboard shows top 10 causal clusters
- [ ] Recommendation engine suggests mutations based on clusters

---

### Phase 3: Session Goal Tracking
**Status**: READY TO IMPLEMENT | **Effort**: 30-45 hours | **Criticality**: HIGH

#### Philosophy
Instead of measuring "did this command succeed?", measure "did the user achieve their overarching goal?" This becomes the primary metric for A/B experiments. A session might have 3 command failures but still achieve its goal (if final output was correct).

#### Pydantic Models
```python
class Session(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    commands_executed: List[str] = []
    inferred_goal: Optional[str] = None
    inferred_goal_confidence: float = 0.0
    
    goal_achieved: Optional[bool] = None
    goal_achievement_confidence: float = 0.0
    goal_achievement_evidence: str = ""
    
    total_tasks_count: int = 0
    successful_tasks_count: int = 0
    failed_tasks_count: int = 0
    
    trace_ids: List[str] = []  # All traces in this session

class SessionMetrics(BaseModel):
    session_id: str
    duration_seconds: float
    task_success_rate: float
    goal_achieved: bool
    goal_achievement_confidence: float
    commands_count: int
```

#### Files to Implement
1. **`session_tracker.py`** (350-450 lines)
   - `start_session()`: Create session
   - `record_command()`: Add command
   - `_infer_goal()`: LLM call every 5 commands
   - `end_session()`: Final evaluation
   - Track session→trace_id relationship

2. **Modify `structured_logger.py`**
   - Add session_id to all LogEntry
   - Track session lifecycle

3. **Integrate with A/B experiments**
   - Use goal_achievement_rate as experiment metric

#### Database Schema
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    
    inferred_goal TEXT,
    inferred_goal_confidence REAL,
    inferred_at TIMESTAMP,
    
    goal_achieved BOOLEAN,
    goal_achievement_confidence REAL,
    goal_evidence TEXT,
    
    total_commands INTEGER DEFAULT 0,
    successful_commands INTEGER DEFAULT 0,
    
    overall_success_rate REAL
);

CREATE TABLE session_traces (
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    PRIMARY KEY (session_id, trace_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (trace_id) REFERENCES causal_traces(trace_id)
);
```

#### Test Specification
```python
# Test: Goal inference and achievement evaluation
@pytest.mark.asyncio
async def test_session_goal_achievement():
    tracker = SessionGoalTracker(mock_llm, mock_db)
    
    # Mock LLM
    mock_llm.call = AsyncMock(side_effect=[
        "Set up and test a FastAPI server",
        '{"achieved": true, "confidence": 0.95, "evidence": "All commands succeeded"}'
    ])
    
    session = await tracker.start_session("session-1")
    
    commands = [
        "pip install fastapi",
        "python -c 'from fastapi import FastAPI'",
        "echo 'FastAPI working'"
    ]
    
    for cmd in commands:
        await tracker.record_command("session-1", cmd)
    
    await tracker.end_session("session-1")
    
    result = await mock_db.fetch("SELECT goal_achieved, inferred_goal FROM sessions")
    assert result[0]["goal_achieved"] == True
    assert "FastAPI" in result[0]["inferred_goal"]
```

#### Definition of Done
- [ ] Session tracking implemented
- [ ] Goal inference happens every 5 commands
- [ ] Goal achievement evaluated on session end
- [ ] Stored correctly in database
- [ ] Test passes
- [ ] Experiments can use goal_achievement_rate metric
- [ ] LLM calls cached to reduce API costs

---

### Phases 4-7 (Summary)

**Phase 4: Real-Time Guidance Injection (Bidirectional IPC)**
- Make IPC bridge bidirectional (currently events flow voice→improver only)
- Send Directive objects back: RouteToCloudDirective, InjectContextDirective
- Voice agent must act within 50ms window
- Files: Modify `ipc_bridge.py`, add directive handler to Jarvis voice agent

**Phase 5: Project Context Graph**
- Store successful session snapshots in ChromaDB
- On new session start, semantic query ChromaDB with first 3 commands
- Pre-load relevant past project context into LLM context window
- Automatically grows over weeks of use
- Files: `project_context_manager.py`

**Phase 6: Mutation Impact Report & Rollback Budget**
- Generate markdown reports 24h after mutation promotion
- Measure delta in success rate, goal achievement rate, latency vs. pre-mutation baseline
- Background task checks every 30min: if metrics dropped >5% with 95% confidence, auto-rollback
- Files: `mutation_impact_engine.py`, background coroutine

**Phase 7: Dataset Quality Scorer**
- Every new validated example: check diversity (semantic distance to nearest neighbor > 0.3)
- Check coverage (all 10 scenario categories > 5%)
- Reject duplicates, flag underrepresented categories
- Dashboard shows SFT dataset health
- Files: `dataset_quality_scorer.py`

---

### Chapter 3: Epistemics (Phases 8-13)

**Phase 8: Confidence Calibration (Temperature Scaling)**
**Status**: READY TO IMPLEMENT | **Effort**: 20-30 hours | **Criticality**: HIGHEST
- Measure true accuracy of predictions bucketed by confidence scores (reliability diagrams).
- Apply temperature scaling ($T$) to logits to match predicted probability with actual success rates.
- *Files:* `calibration.py` (`CalibrationTracker`, `fit_temperature()`)

**Phase 9: Adversarial Probing (Red-Teaming)**
- Use the cloud LLM to generate ambiguous/edge-case inputs across the 10 SFT categories.
- Test against the live system and use failures as hard negative examples in the SFT dataset.
- *Files:* `red_teaming.py` (`RedTeamEngine`)

**Phase 10: Skill Crystallization (Proceduralization)**
- Identify sequences of commands that repeatedly achieve the same goal.
- Compile these into named "Skills" (macros) with preconditions that bypass full LLM inference for extreme speedups.
- *Files:* `skill_library.py`

**Phase 11: Predictive Failure Prevention**
- Train a lightweight model (e.g., Logistic Regression via `scikit-learn`) on historical `CausalTrace` features (prompt length, intent, warming, active sessions).
- If failure probability > threshold (e.g., 0.7), proactively route to the cloud fallback instead of failing locally.
- *Files:* `failure_predictor.py`

**Phase 12: Knowledge Distillation (Fighting Instruction Debt)**
- Combat "instruction debt" from accumulating mutation rules.
- Periodically prompt the LLM to compress `instructions.md` using the last 90 days of successful traces, outputting a consolidated, non-contradictory instruction set.
- *Files:* `distillation_engine.py`

**Phase 13: Multi-Objective Pareto Optimization**
- Expand A/B experiment evaluation from a single metric (success rate) to multiple (success rate, latency, cost, memory use).
- Evaluate if treatment is Pareto-better (better on at least one, worse on none) before promotion.
- *Files:* `pareto_evaluator.py`

---

### Chapter 4: Meta-Learning (Phase 14)

**Phase 14: Prompt Evolution Engine (Learning How to Learn)**
**Status**: READY TO IMPLEMENT | **Effort**: 25-35 hours | **Criticality**: HIGH
- Transition the system from a first-order learner (fixed critique prompt) to a second-order meta-learner.
- Treat critique prompt templates as evolving parameters via a genetic algorithm.
- Maintain a population of prompt variants and track their **Yield Rate** (fraction of generated mutations that are promoted by A/B tests).
- Evolve the population by culling low-yield prompts and prompting an LLM to "cross-over" and mutate the structural features of top-performing prompts to spawn the next generation.
- *Files:* `prompt_evolution.py` (`PromptEvolutionEngine`)

---

## 6. Execution Rules for AI Agents
*   **Read before you write**: If you are unsure of an interface, read `executor.py`, `dashboard_api.py`, or `fast_router.py` before modifying.
*   **Verify syntax**: Ensure imports exist (e.g., `scipy`, `sentence-transformers`, `chromadb`). Add them to `requirements.txt` / install them if missing.
*   **Step-by-Step**: Execute the sprint in order (Phases 1 -> 7). Do not skip to Phase 7 without the Phase 1/2 tracking infrastructure in place. 
*   **Test as you go**: Implement the specific Test Spec for the phase before marking it done.
*   **Database First**: Create all tables before implementing code. Schema must be stable before implementation.
*   **Backward Compatibility**: Existing tests must pass. If they don't, fix your changes, not the tests.

---

## 7. Testing Strategy (All Phases)

### Unit Tests (Per Module)
- Mock all external dependencies (LLM, DB, IPC)
- Test happy path and error cases
- Minimum 80% code coverage

### Integration Tests
- End-to-end: user input → router → executor → log → trace → autopsy → mutation → experiment
- Multi-phase: phase 1 + phase 2, phase 2 + phase 3, etc.
- Real DB (SQLite in-memory) where possible

### Regression Tests
- Run existing test suite after each phase
- Measure performance before/after
- Alert if metrics degrade >5%

### Load Tests (Phases 3+)
- 1000+ concurrent sessions
- 10K traces in causal clustering
- Vector search latency <100ms

---

## 8. Configuration Reference

### Environment Variables
```bash
# Phase 1: Experiments
EXPERIMENT_TRAFFIC_SPLIT=0.10
EXPERIMENT_MIN_SAMPLES=50

# Phase 2: Causal Tracing
ENABLE_CAUSAL_TRACING=true
TRACE_STORAGE_BACKEND=sqlite

# Phase 3: Session Tracking
SESSION_INACTIVITY_TIMEOUT=60
SESSION_GOAL_INFER_INTERVAL=5

# Phase 4: IPC
IPC_PIPE_NAME=\\\\.\\pipe\\jarvis_improver
IPC_DIRECTIVE_TIMEOUT_MS=50

# Phase 5: Project Contexts
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
PROJECT_CONTEXT_TOP_K=3

# Phase 6: Impact Reports
MUTATION_IMPACT_CHECK_INTERVAL_MIN=30
DEGRADATION_THRESHOLD_PCT=5
DEGRADATION_CONFIDENCE=0.95

# Phase 7: Dataset Quality
DATASET_DIVERSITY_THRESHOLD=0.3
DATASET_COVERAGE_MIN_PCT=5
```

---

## 9. Success Metrics (Sprint Completion)

| Phase | Success Criteria |
|-------|-----------------|
| 1 | Experiment statistical test passes; p<0.05 for 20% improvement |
| 2 | Causal clusters identified; 2+ conditions per cluster |
| 3 | Session goal inferred; achievement evaluated with 0.8+ confidence |
| 4 | Directive fires; voice agent responds within 50ms |
| 5 | ChromaDB returns top-3 projects; context injected |
| 6 | Impact report generated; auto-rollback triggered on degradation |
| 7 | Duplicates rejected; underrepresented categories flagged |

---

**This is the authoritative specification. All agents refer to this document first.**

Version: 2.0.0 | Status: Ready for Implementation | Last Updated: 2026-03-07
