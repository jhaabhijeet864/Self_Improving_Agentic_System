# Jarvis-OS 7-Phase Implementation: Quick Reference

## Overview
Transform Jarvis-OS from a basic agent framework into a self-improving, statistically-validated, causally-traced system that learns user project patterns and safely deploys mutations.

**Timeline**: 7 weeks | **Effort**: 280-350 hours | **Teams**: 1-3 engineers

---

## Phase Sequence (Must Do in Order)

### ✅ Phase 1: Controlled Experiments (Week 1)
**Files**: `experiment_engine.py`, modify `fast_router.py`  
**Goal**: Replace human approval binary with A/B testing using scipy.stats

```python
# Core idea: 10% traffic to treatment, 90% to control, evaluate with proportions_ztest
experiment = ExperimentEngine.create_experiment(mutation)
executor_id, is_treatment, exp_id = await engine.route_with_experiment(query)
# After 50 samples per group: evaluate() returns winner
result = await engine.evaluate(experiment)  # → ExperimentResult
```

**DoD Checklist**:
- [ ] proportions_ztest correctly detects p<0.05 when treatment 20% better
- [ ] Experiment outcomes logged with experiment_id for segmentation
- [ ] Database tables created and verified
- [ ] Test passes without mocking the statistical library

---

### ✅ Phase 2: Causal Tracing (Week 2)
**Files**: `causal_tracer.py`, modify `structured_logger.py`  
**Goal**: Propagate trace_id through every component; cluster failures by root cause

```python
# Core idea: trace_id flows through router→executor→memory→llm→outcome
# Enables: "All failures when prompt > 2000 tokens on local executor"
tracer = CausalTracer(db)
trace_id = await tracer.start_trace(session_id, user_input)
# ... components update the same trace ...
clusters = await tracer.find_causal_clusters(error_category="LLMOutputMalformed")
# → List[CausalCluster] with conditions like {"executor": "local", "prompt_gt_2000": True}
```

**DoD Checklist**:
- [ ] trace_id consistently present in all logs
- [ ] CausalCluster identifies 2+ conditions (executor AND prompt_length)
- [ ] Autopsy.find_causal_clusters() works
- [ ] Dashboard shows top 10 clusters

---

### ✅ Phase 3: Session Goal Tracking (Week 2-3)
**Files**: `session_tracker.py`, modify logging  
**Goal**: Evaluate session-level goals, not just per-command success

```python
# Core idea: Every 5 commands, infer goal via LLM
# On session end, evaluate achievement
# Use goal_achievement_rate as A/B test metric (better signal than task_success_rate)
tracker = SessionGoalTracker(llm_provider, db)
await tracker.record_command("session-1", "pip install fastapi")
# After 5 commands: LLM infers "Set up FastAPI server"
# At end: LLM evaluates "Did they achieve it?" → 95% confident YES
```

**DoD Checklist**:
- [ ] Goal inferred every 5 commands
- [ ] Achievement evaluated with confidence score
- [ ] Stored correctly in sessions table
- [ ] Experiments can use goal_achievement_rate as metric
- [ ] LLM calls cached to save API cost

---

### ✅ Phase 4: Bidirectional IPC (Week 3-4)
**Files**: Modify `ipc_bridge.py`, add directive handler to Jarvis voice agent  
**Goal**: Self-improver can send Directive objects back to voice agent in real-time

```python
# Core idea: Instead of just observing, actively guide
# "Next request to cloud" → RouteToCloudDirective
# "Pre-load React context" → InjectContextDirective
# Voice agent must respond within 50ms
directive = RouteToCloudDirective(target_tasks_count=5)
await improver.send_directive(directive)  # Over IPC
# Voice agent receives, acts immediately
```

**DoD Checklist**:
- [ ] IPC bridge sends and receives messages
- [ ] Voice agent has directive handler
- [ ] Latency <50ms measured
- [ ] Directive types: RouteToCloud, InjectContext

---

### ✅ Phase 5: Project Context Graph (Week 4-5)
**Files**: `project_context_manager.py`, extend ChromaDB usage  
**Goal**: Remember successful project patterns; auto-load context for new sessions

```python
# Core idea: Session succeeds → store command sequence + goal as project snapshot
# New session starts → semantic query ChromaDB for similar past projects
# Inject context via Phase 4 IPC
context_mgr = ProjectContextManager(chromadb_client)
# On successful session: snapshot stored
await context_mgr.store_project_snapshot(session_goal, command_sequence)
# On new session:
similar_projects = await context_mgr.query_similar(first_3_commands)
await improver.send_directive(InjectContextDirective(contexts=similar_projects))
```

**DoD Checklist**:
- [ ] Successful sessions stored as snapshots
- [ ] ChromaDB semantic search returns top-3
- [ ] Context injected automatically
- [ ] Test: React bugfix snapshot retrieved for new React task

---

### ✅ Phase 6: Mutation Impact Report & Auto-Rollback (Week 5-6)
**Files**: `mutation_impact_engine.py`, background coroutine  
**Goal**: Generate reports, auto-rollback degrading mutations

```python
# Core idea: 24h after promotion, measure delta in metrics
# Every 30min: if success_rate dropped >5% with 95% confidence → rollback
# Generate markdown reports in mutations/impact_reports/
engine = MutationImpactEngine(db)
# Background task runs every 30 minutes
impact_report = await engine.generate_impact_report(mutation_id)
# impact_{mutation_id}.md with success_rate delta, goal_achievement_rate delta, etc.

# If bad: auto_result = await engine.check_for_degradation()
# → triggers snapshot_based_rollback(), sends MutationAutoRolledBackEvent
```

**DoD Checklist**:
- [ ] Impact report generated 24h post-promotion
- [ ] Markdown report includes delta in 3+ metrics
- [ ] Background task checks every 30min
- [ ] Auto-rollback triggered on >5% degradation
- [ ] Dashboard shows mutation history

---

### ✅ Phase 7: Dataset Quality Scorer (Week 6-7)
**Files**: `dataset_quality_scorer.py`  
**Goal**: Prevent mode collapse in SFT fine-tuning data

```python
# Core idea: Every new validated example (input, output) pair
# Check diversity: cosine distance to nearest neighbor > 0.3
# Check coverage: all 10 scenario categories maintain > 5%
# Reject duplicates, flag underrepresented
scorer = DatasetQualityScorer(db, embeddings_model)
quality = await scorer.evaluate_new_example(new_input, new_output)
# Returns: {"quality_score": 0.92, "diversity": 0.85, "coverage_recommendation": "Add more file_search"}

# Dashboard: Donut chart of scenario distribution + diversity gauge
```

**DoD Checklist**:
- [ ] Duplicates rejected (distance < 0.3)
- [ ] Underrepresented categories flagged
- [ ] Dataset metrics exposed to dashboard
- [ ] Test: submit duplicate → rejected; submit underrep category → flagged

---

## Database Schema Additions (Cumulative)

### Phase 1: Experiments
```sql
CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    mutation_id TEXT,
    traffic_split REAL,
    status TEXT,
    started_at TIMESTAMP
);
```

### Phase 2: Causal Tracing
```sql
CREATE TABLE causal_traces (
    trace_id TEXT PRIMARY KEY,
    session_id TEXT,
    router_executor TEXT,
    prompt_tokens INTEGER,
    error_category TEXT,
    outcome TEXT,
    created_at TIMESTAMP
);
```

### Phase 3: Session Tracking
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    inferred_goal TEXT,
    goal_achieved BOOLEAN,
    goal_achievement_confidence REAL
);
```

### Phases 4-7
- `directives` table
- `project_contexts` (ChromaDB)
- `mutation_impact_reports`
- `dataset_metrics`

---

## Agent Personas & Instructions

### GitHub Copilot
**Best for**: Implementing core modules, code generation, refactoring  
**Style**: Code-first, references to existing patterns, expects full file edits  
**Prompt template**: "In phase-1-experiment.py, implement ExperimentEngine class with these methods: create_experiment(), route_with_experiment(), evaluate(). Use scipy.stats.proportions_ztest for the statistical test."

### Claude
**Best for**: Architecture, design tradeoffs, explaining complex logic  
**Style**: Long-context reasoning, design docs first, then code  
**Prompt template**: "Design the interaction between Phase 1 (experiments) and Phase 5 (project contexts). How does the project context influence the traffic_split parameter? Should we use different thresholds for different project types?"

### Gemini CLI
**Best for**: Database schema, batch operations, API performance  
**Style**: Task-oriented, throughput focus, API-first  
**Prompt template**: "Design the schema for causal_traces table to optimize for: 1) GROUP BY executor + error_category queries, 2) Scanning by session_id, 3) Archival after 90 days. Use appropriate indices."

### Cursor/IDE Agents
**Best for**: Multi-file changes, integration work, refactoring  
**Style**: File paths, line numbers, before/after context  
**Prompt template**: "Phase 2 requires adding trace_id to all log calls. Files to update: structured_logger.py (line 45-60), executor.py (line 120-150), memory_manager.py (line 80-100). Show me the before/after for each."

---

## Testing Strategy

### Unit Tests (Per Phase)
- Mock LLM, DB, IPC
- Happy path + error cases
- >80% coverage

### Integration Tests
- Phase 1 + Phase 2 (trace_id in experiments)
- Phase 3 + Phase 1 (goal_achievement_rate as metric)
- Full pipeline: input → router → executor → log → autopsy

### Regression Tests
- Existing tests must pass
- Performance benchmarks: <2% degradation
- Rollback to previous phase if tests fail

---

## Key Success Metrics

| Phase | Success Criteria | Validation |
|-------|-----------------|-----------|
| 1 | p < 0.05 for 20% improvement | Test passes; real experiment run |
| 2 | Clusters with 2+ conditions | Autopsy.find_causal_clusters() works |
| 3 | Goal inferred + achieved evaluated | Sessions table populated; confidence > 0.8 |
| 4 | Directive response < 50ms | Measure latency; voice agent logs |
| 5 | Top-3 projects retrieved | ChromaDB query works; context injected |
| 6 | Report generated + auto-rollback | impact_*.md exists; rollback triggered |
| 7 | Duplicates rejected | Dataset metrics improve |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM API costs | Cache goal inferences; use cheap model (Gemini nano) |
| Experiment timeout | Set max_samples limit; auto-promote after 1000 samples |
| IPC latency | Use WebSocket instead of named pipes if >50ms |
| ChromaDB scale | Batch embeddings; limit projects to 1000 snapshots |
| Auto-rollback bugs | Require approval for rollback; test thoroughly first |

---

## Deployment Checklist

- [ ] All 7 phases implemented
- [ ] All tests passing
- [ ] Database schema migrations working
- [ ] Dashboard updated with new sections
- [ ] Environment variables documented
- [ ] Performance regression <2%
- [ ] Rollback procedure tested
- [ ] Team trained on new features
- [ ] Monitoring/alerting configured
- [ ] Customer communication plan

---

**Status**: Ready to Implement  
**Start Date**: ASAP  
**Target Completion**: 7 weeks  
**Assigned to**: [AI Agent Teams]
