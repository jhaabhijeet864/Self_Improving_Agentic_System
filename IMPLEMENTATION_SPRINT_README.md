# Jarvis-OS: Complete Implementation Sprint

## 📋 Documentation Roadmap

This repository now contains **4 authoritative documents** that guide all development. Start here:

### 1. **AGENT_SYSTEM_PROMPT.md** (Main)
- **Purpose**: System-wide context, personas, schemas, all 7 phases in detail
- **Audience**: All AI agents, architects, reviewers
- **Length**: ~4000 lines
- **Sections**:
  - Mission statement
  - Agent personas (Copilot, Claude, Gemini, Cursor)
  - Pydantic schemas for all phases
  - Phase 1-7 detailed specifications with test specs
  - Execution rules and testing strategy

**Start here if**: You're a new agent joining the project

### 2. **7_PHASE_SUMMARY.md** (This File's Companion)
- **Purpose**: Quick reference checklist; phase-by-phase DoD
- **Audience**: Project managers, sprint planners
- **Length**: ~1200 lines (condensed)
- **Sections**:
  - Phase sequence (must do in order)
  - Per-phase checklist and file list
  - Database schema additions
  - Risk mitigation table

**Start here if**: You're planning sprints or reviewing progress

### 3. **phase_implementation_guide.md** (In Session Folder)
- **Purpose**: Detailed pseudocode, SQL, test code for Phases 1-3
- **Audience**: Implementation agents
- **Length**: ~26KB
- **Sections**:
  - Complete code examples (not pseudocode) for Phases 1-3
  - SQL migrations
  - Exact test specifications

**Start here if**: You're implementing Phase 1, 2, or 3

### 4. **copilot-instructions.md** (Project Root)
- **Purpose**: Repository conventions, build/test/lint, architecture
- **Audience**: All developers
- **Length**: ~16KB
- **Sections**:
  - How to build/test/lint
  - High-level architecture
  - Key conventions
  - Configuration patterns

**Start here if**: You're new to the codebase

---

## 🎯 Current Status

### Completed ✅
- [x] Code structure analysis and copilot-instructions.md created
- [x] 20-gap architectural audit and plan created
- [x] 12 dashboard UI fixes implemented and tested
- [x] AGENT_SYSTEM_PROMPT.md with 7-phase specifications
- [x] Database schemas designed for all phases
- [x] Pydantic models defined for all phases
- [x] Test specifications for all phases
- [x] Phase dependencies mapped

### Ready to Implement (Pending) ⏳
- [ ] **Phase 1**: Controlled Experiments (40-60 hrs)
- [ ] **Phase 2**: Causal Tracing (35-50 hrs)
- [ ] **Phase 3**: Session Goal Tracking (30-45 hrs)
- [ ] **Phase 4**: Bidirectional IPC (25-35 hrs)
- [ ] **Phase 5**: Project Context Graph (20-30 hrs)
- [ ] **Phase 6**: Mutation Impact & Rollback (25-35 hrs)
- [ ] **Phase 7**: Dataset Quality Scoring (20-30 hrs)

**Total Effort**: 280-350 engineer-hours | **Timeline**: 7-10 weeks with 1-2 engineers

---

## 🏗️ How Each Document Is Used

### When Implementing Code
1. **Read** AGENT_SYSTEM_PROMPT.md "Phase X" section
2. **Reference** phase_implementation_guide.md for pseudocode/test specs
3. **Check** 7_PHASE_SUMMARY.md DoD checklist before marking complete
4. **Apply** copilot-instructions.md conventions (logging, async patterns, etc.)

### When Planning Work
1. **Check** 7_PHASE_SUMMARY.md phase sequence (must be in order)
2. **Review** SQL database schema additions
3. **Read** risk mitigation table
4. **Estimate** effort and timeline

### When Reviewing PRs
1. **Verify** test specs pass (from AGENT_SYSTEM_PROMPT.md)
2. **Check** pydantic models match (exact field names)
3. **Validate** database migrations applied
4. **Ensure** no breaking changes to existing tests

---

## 🚀 Getting Started (For First Agent)

### Step 0: Understand the Mission
- Read: AGENT_SYSTEM_PROMPT.md sections "Mission Statement" and "Project Context"
- Time: 15 minutes
- Goal: Know WHY this system exists (self-improvement loop)

### Step 1: Understand the Architecture
- Read: copilot-instructions.md "High-Level Architecture"
- Read: AGENT_SYSTEM_PROMPT.md "Project Context & Architecture Knowledge"
- Time: 30 minutes
- Goal: Know HOW the components fit together

### Step 2: Understand Phase 1
- Read: AGENT_SYSTEM_PROMPT.md "Phase 1: Controlled Experiment Framework"
- Read: phase_implementation_guide.md entire Phase 1 section
- Time: 1 hour
- Goal: Know WHAT to build and WHY it matters

### Step 3: Start Phase 1 Implementation
- Create: `experiment_engine.py`
- Modify: `fast_router.py` (add `route_with_config`)
- Create: Database tables
- Implement: Test spec
- Time: 40-60 hours
- Success: Test passes with p<0.05 on 20% improvement

---

## 📊 Dependency Tree (Phases Must Be Sequential)

```
Phase 1 (Experiments)
    ↓
Phase 2 (Causal Tracing)
    ├─ Uses trace_id from Phase 1
    ├─ Extends logging from Phase 1
    ↓
Phase 3 (Session Goals)
    ├─ Uses sessions table from Phase 2
    ├─ Integrates with experiments from Phase 1
    ↓
Phase 4 (Bidirectional IPC)
    ├─ Sends directives to voice agent
    ├─ Based on data from Phases 1-3
    ↓
Phase 5 (Project Context)
    ├─ Stores successful sessions from Phase 3
    ├─ Sends context via Phase 4 IPC
    ↓
Phase 6 (Impact Reports & Rollback)
    ├─ Measures impact using Phase 3 metrics
    ├─ Triggers rollback for Phase 1 experiments
    ↓
Phase 7 (Dataset Quality)
    └─ Consumes validated data from all phases
```

**Critical Path**: Phases 1→2→3 (must complete in order before Phase 4)

---

## 🔍 Key Schemas (Quick Reference)

### Experiment (Phase 1)
```python
Experiment(
    mutation_id, 
    traffic_split=0.10,    # 10% to treatment
    min_samples=50,        # Run until 50 per group
    status="running"       # → "promoted" or "rejected"
)
```

### CausalTrace (Phase 2)
```python
CausalTrace(
    trace_id,              # Flows through all components
    router_executor,       # Where routed to
    prompt_tokens,         # How large the prompt
    error_category,        # Classification
    outcome                # success|failed
)
```

### Session (Phase 3)
```python
Session(
    inferred_goal,         # "Set up FastAPI server"
    goal_achieved,         # True/False
    goal_achievement_confidence  # 0.95
)
```

All schemas in: **AGENT_SYSTEM_PROMPT.md section 3**

---

## 🧪 Test Specifications (One Per Phase)

### Phase 1 Test
```
Simulate 100 requests (50/50 control/treatment)
Treatment has 20% higher success rate
Assert: winner=="treatment" AND p_value < 0.05
```

### Phase 2 Test
```
Create 10 failed traces: local executor, prompt>2000 tokens
Assert: find_causal_clusters() returns cluster with both conditions
```

### Phase 3 Test
```
Feed 6 mock commands about FastAPI
Assert: inferred_goal contains "FastAPI" AND goal_achieved==True
```

**See full test specs**: AGENT_SYSTEM_PROMPT.md for each phase

---

## ⚙️ Configuration (Environment Variables)

### Phase 1
```bash
EXPERIMENT_TRAFFIC_SPLIT=0.10
EXPERIMENT_MIN_SAMPLES=50
```

### Phase 3
```bash
SESSION_INACTIVITY_TIMEOUT=60
SESSION_GOAL_INFER_INTERVAL=5
```

### Phase 5
```bash
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
```

### Phase 6
```bash
MUTATION_IMPACT_CHECK_INTERVAL_MIN=30
DEGRADATION_THRESHOLD_PCT=5
```

**Full list**: AGENT_SYSTEM_PROMPT.md section 8

---

## 📈 Success Metrics

### Phase 1
- Statistical test correctly identifies 20% improvement (p<0.05)
- Experiment outcomes logged and queryable
- No performance regression vs. existing router

### Phase 2
- trace_id present in 100% of logs
- Causal clusters identified with 2+ conditions
- Autopsy can explain failures

### Phase 3
- Goal inferred for 100% of sessions
- Achievement evaluated with >0.8 confidence
- goal_achievement_rate usable as A/B test metric

### Phases 4-7
- See AGENT_SYSTEM_PROMPT.md "Success Metrics" section

---

## 🐛 Common Pitfalls

### ❌ Don't
- Skip Phase 1→2→3 sequence (later phases depend on earlier infrastructure)
- Mock the scipy.stats.proportions_ztest in Phase 1 test (test the real statistical behavior)
- Forget trace_id in any logging call (defeats Phase 2 causal tracing)
- Use synchronous DB calls in async code (use aiosqlite)

### ✅ Do
- Run existing tests before and after each phase
- Create database tables before implementing code
- Add new Pydantic models to jarvis_common/schemas.py
- Test on real data (50+ samples) before marking done

---

## 📞 Questions?

### For architecture questions
→ Read: AGENT_SYSTEM_PROMPT.md "Project Context"

### For implementation details
→ Read: phase_implementation_guide.md for your phase

### For conventions and patterns
→ Read: copilot-instructions.md

### For progress tracking
→ Check: SQL todos table (created in session)

---

## 📄 All Documents at a Glance

| File | Purpose | Length | Audience |
|------|---------|--------|----------|
| **AGENT_SYSTEM_PROMPT.md** | System specs + 7-phase details | 4000L | All agents |
| **7_PHASE_SUMMARY.md** | Quick checklist + DoD | 1200L | PMs, reviewers |
| **phase_implementation_guide.md** | Pseudocode + tests | 26KB | Implementers |
| **copilot-instructions.md** | Repo conventions | 16KB | Developers |
| **IMPLEMENTATION_SPRINT_README.md** | This file | 500L | Onboarding |

---

## 🎓 Learning Path for New Agents

1. **Day 1**: Read AGENT_SYSTEM_PROMPT.md + copilot-instructions.md (2 hours)
2. **Day 2**: Read phase_implementation_guide.md (1 hour)
3. **Day 3**: Start Phase 1 implementation (30-40 hours over 3-5 days)
4. **Code Review**: Submit PR, get feedback, iterate
5. **Repeat**: Move to Phase 2

**Total onboarding**: 1 week to first PR

---

## ✅ Verification Checklist Before Starting Phase 1

- [ ] Read AGENT_SYSTEM_PROMPT.md (all sections)
- [ ] Read phase_implementation_guide.md Phase 1
- [ ] Understand scipy.stats.proportions_ztest
- [ ] Verify scipy is in requirements.txt
- [ ] Review existing router.py to understand config format
- [ ] Create experiment_engine.py (skeleton)
- [ ] Understand database schema additions
- [ ] Review test specification
- [ ] Verify aiosqlite is available
- [ ] Ready to implement

---

**Status**: 🟢 Ready for Implementation  
**Last Updated**: 2026-03-07  
**Next Steps**: Assign Phase 1 to first agent
