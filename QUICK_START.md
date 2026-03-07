# 🚀 Jarvis-OS: Quick Start Guide

## TL;DR

You have **4 documents**. Here's which to read when:

### 🎯 I'm Planning Work
**Read**: `7_PHASE_SUMMARY.md` (10 min)
- Phase checklist, effort estimates, dependencies

### 📖 I'm New to the Project
**Read**: `IMPLEMENTATION_SPRINT_README.md` (30 min)
- What was built, what's next, learning path

### 💻 I'm Starting Phase 1
**Read**: `AGENT_SYSTEM_PROMPT.md` Phase 1 section (1 hour)  
**Read**: `phase_implementation_guide.md` Phase 1 section (1 hour)  
**Then**: Start coding (40-60 hours)

### 📚 I Need Full Context
**Read**: `AGENT_SYSTEM_PROMPT.md` (2 hours)
- Complete spec for all 7 phases

---

## 📋 Status

### ✅ Complete
- Dashboard fixed (12/12 issues)
- Documentation written
- SQL todos created
- Pydantic schemas designed
- Database migrations planned
- Test specs written

### ⏳ Pending
- Phase 1: Controlled Experiments
- Phase 2: Causal Tracing
- Phase 3: Session Goal Tracking
- Phase 4: Bidirectional IPC
- Phase 5: Project Context Graph
- Phase 6: Mutation Impact & Rollback
- Phase 7: Dataset Quality

---

## 🎯 The Mission

Build a **self-improving AI agent** that:
1. **Experiments** with mutations safely (A/B testing)
2. **Traces causes** of failures (distributed tracing)
3. **Learns goals** across commands (session tracking)
4. **Guides itself** in real-time (bidirectional IPC)
5. **Remembers projects** (semantic memory)
6. **Rolls back failures** automatically (impact monitoring)
7. **Maintains data quality** (dataset health scoring)

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| Total Documentation | 7000+ lines |
| Pydantic Models | 15+ models defined |
| Database Tables | 12+ tables designed |
| Test Specs | 7 detailed specs |
| Phase Dependencies | Linear (1→2→3→...→7) |
| Estimated Hours | 280-350 hours |
| Team Size | 1-3 engineers |
| Timeline | 7-10 weeks |
| Critical Path | Phases 1-3 first |

---

## 🔥 Phase 1 (Week 1)

**Goal**: A/B test mutations using scipy.stats  
**Core Code**: `experiment_engine.py`  
**Lines**: ~400-500  
**Test**: Detect 20% improvement with p<0.05  

```python
# High-level flow:
experiment = await engine.create_experiment(mutation, traffic_split=0.10)
executor_id, is_treatment = await engine.route_with_experiment(query)
# After 50 samples per group...
result = await engine.evaluate(experiment)  # → winner="treatment" if p<0.05
```

**Start Date**: Tomorrow ✅  
**Effort**: 40-60 hours  
**Blocker**: None

---

## 🔥 Phase 2 (Week 2)

**Goal**: Trace causes of failures through full pipeline  
**Core Code**: `causal_tracer.py`  
**Lines**: ~300-400  
**Test**: Cluster failures by 2+ conditions (executor + prompt_length)  

```python
# High-level flow:
trace_id = await tracer.start_trace(session_id, user_input)
# ... all components update same trace ...
clusters = await tracer.find_causal_clusters(error_category)
# → CausalCluster with conditions like {"executor": "local", "prompt_gt_2000": true}
```

**Blocker**: Phase 1 complete  
**Prerequisite**: trace_id flows through all components

---

## 🔥 Phase 3 (Week 2-3)

**Goal**: Track multi-command user goals and achievement  
**Core Code**: `session_tracker.py`  
**Lines**: ~350-450  
**Test**: Infer goal from 6 FastAPI commands, evaluate achievement  

```python
# High-level flow:
tracker = SessionGoalTracker(llm_provider, db)
await tracker.record_command("session-1", "pip install fastapi")
# Every 5 commands: LLM infers goal
# On session end: LLM evaluates achievement with confidence
```

**Blocker**: Phase 2 complete  
**New Metric**: Use goal_achievement_rate in A/B experiments

---

## 📁 Files You'll Use

### Main Documents (Project Root)
```
AGENT_SYSTEM_PROMPT.md                 ← Master spec (4000 lines)
7_PHASE_SUMMARY.md                     ← Quick checklist
IMPLEMENTATION_SPRINT_README.md        ← Onboarding guide
DELIVERABLES_SUMMARY.md                ← What's been done
QUICK_START.md                         ← This file
copilot-instructions.md                ← Repo conventions
```

### Session Planning (Session Folder)
```
phase_implementation_guide.md          ← Detailed pseudocode for Phases 1-3
plan.md                                ← 20-gap architectural plan
```

### Existing Docs (Keep Current)
```
README_FULL.md                         ← Overview
STATUS_REPORT.md                       ← Progress tracking
```

---

## 🧑‍💻 For Each Agent Type

### GitHub Copilot
- **Use**: For code generation and refactoring
- **Style**: Code-first, concise
- **Example**: "In `experiment_engine.py`, implement the ExperimentEngine class using scipy.stats.proportions_ztest"

### Claude
- **Use**: For architecture and design
- **Style**: Long-context reasoning
- **Example**: "Explain the interaction between Phase 1 experiments and Phase 3 session goals. How should we integrate them?"

### Gemini
- **Use**: For database and performance
- **Style**: Task-oriented
- **Example**: "Design the `experiment_outcomes` table to optimize for queries grouping by (experiment_id, is_treatment) and filtering by recorded_at"

### Cursor IDE
- **Use**: For multi-file integration
- **Style**: File paths and line numbers
- **Example**: "Add trace_id parameter to all logging calls in: structured_logger.py (line 45-60), executor.py (line 120-150), memory_manager.py (line 80-100)"

---

## ⚡ Critical Success Factors

### Must Do
- [ ] Read AGENT_SYSTEM_PROMPT.md before starting any phase
- [ ] Follow Pydantic field names exactly
- [ ] Create database tables before coding
- [ ] Phases must be sequential (1→2→3→...)
- [ ] Test before marking "done"

### Must Not Do
- [ ] Skip to Phase 7 without 1-3 infrastructure
- [ ] Use dummy code or `pass` blocks in core logic
- [ ] Mock scipy.stats.proportions_ztest in Phase 1 test
- [ ] Forget trace_id in logging calls
- [ ] Break existing tests

---

## 🎯 Success Metrics

**Phase 1**: proportions_ztest detects 20% difference  
**Phase 2**: Causal clusters group by 2+ conditions  
**Phase 3**: Goal inferred with >0.8 confidence  
**Phase 4**: Directives executed <50ms  
**Phase 5**: Top-3 projects retrieved semantically  
**Phase 6**: Auto-rollback on >5% degradation  
**Phase 7**: Dataset diversity maintained >0.3  

---

## 🚨 Common Mistakes

| ❌ Don't | ✅ Do |
|---------|------|
| Skip reading AGENT_SYSTEM_PROMPT.md | Read it first (always) |
| Mock proportions_ztest | Test real statistical behavior |
| Use sync DB in async code | Use aiosqlite |
| Skip database schema | Create tables before coding |
| Hardcode field names | Use exact Pydantic names |
| Break existing tests | Maintain backward compatibility |

---

## 📞 Help

### **Q: Which document should I read?**
A: See the table at top of this file

### **Q: How do I implement Phase [X]?**
A: Read AGENT_SYSTEM_PROMPT.md "Phase X" section (detailed specs)

### **Q: Where's the code?**
A: phase_implementation_guide.md has pseudocode for Phases 1-3

### **Q: What's the test spec?**
A: AGENT_SYSTEM_PROMPT.md or phase_implementation_guide.md for your phase

### **Q: How are phases sequenced?**
A: Read 7_PHASE_SUMMARY.md "Phase Sequence" section

### **Q: When am I done?**
A: Check the "Definition of Done" in 7_PHASE_SUMMARY.md for your phase

---

## 🏁 Next Steps

1. **Assign Phase 1** to first engineer
2. **Engineer reads**: AGENT_SYSTEM_PROMPT.md + phase_implementation_guide.md
3. **Engineer implements**: experiment_engine.py (40-60 hours)
4. **Review**: Test passes + no regressions
5. **Merge**: Mark todo as "done"
6. **Repeat**: Phase 2, 3, 4...

---

## 📊 Progress Dashboard

```
Phase 1: Controlled Experiments           ▯ Pending (40-60 hrs)
Phase 2: Causal Tracing                   ▯ Pending (35-50 hrs)
Phase 3: Session Goal Tracking            ▯ Pending (30-45 hrs)
Phase 4: Bidirectional IPC                ▯ Pending (25-35 hrs)
Phase 5: Project Context Graph            ▯ Pending (20-30 hrs)
Phase 6: Mutation Impact & Rollback       ▯ Pending (25-35 hrs)
Phase 7: Dataset Quality Scoring          ▯ Pending (20-30 hrs)

Critical Path (Phases 1-3):               ▯ Pending (105-155 hrs)
Timeline:                                 7-10 weeks
Status:                                   🟢 Ready to Start
```

---

**You have everything needed. Time to code! 🚀**

**Start with**: `AGENT_SYSTEM_PROMPT.md` Phase 1 section
