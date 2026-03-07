# Jarvis-OS: Project Manifest (20-Gap Roadmap)

**Status:** 🚧 INCOMPLETE

This manifest acts as the **Single Source of Truth** for the project's actual implementation status. It tracks the 20 actionable gaps identified in `SYSTEM_PROMPT.md` required to transform the current codebase into a production-ready autonomous QA and learning infrastructure.

---

## 📋 Gaps & Deliverables

### Phase 1: Core Audit and Tooling
- [ ] **Gap 0:** Mandatory Code Audit (`audit.py` creation and execution on all 7 core modules).
- [ ] **Gap 20:** Honest code rewrite of any bloated files highlighted in Gap 0.

### Phase 2: Autonomous Intelligence
- [ ] **Gap 1:** Real LLM Integration (`SelfCritiqueEngine` using Cloud LLMs for structured JSON critiques).
- [ ] **Gap 2:** ML Routing Classifier (`LocalClassifier` via `sentence-transformers`).
- [ ] **Gap 11:** Active use of SFT Dataset via `SFTDatasetManager`.

### Phase 3: Infrastructure and Security
- [ ] **Gap 3:** IPC Bridge Data Interchange (`jarvis_common/ipc_bridge.py` websocket server/client).
- [ ] **Gap 6:** Sandboxed Subprocess Execution (PyWin32 Windows Job Objects limits).
- [ ] **Gap 8:** Dashboard Authentication (JWT authentication for FastAPI).
- [ ] **Gap 16:** Windows Daemon service wrapper (`windows_service.py`).
- [ ] **Gap 18:** API Rate Limiting (SlowAPI limits per endpoint).

### Phase 4: State Management and Storage
- [ ] **Gap 7:** ChromaDB Vector Storage for Long-Term Memory.
- [ ] **Gap 9:** SQLite Persistence via asynchronous SQLAlchemy (`db/models.py`).
- [ ] **Gap 19:** Shared Contracts / Version schemas (`jarvis_common/schemas.py`).

### Phase 5: Telemetry and Diagnostics
- [ ] **Gap 10:** Structured Error Classification Taxonomy (`error_taxonomy.py`).
- [ ] **Gap 12:** Latency Budgeting Circuit Breaker (`latency_budget.py`).
- [ ] **Gap 14:** Event Telemetry Source fields for log disambiguation.

### Phase 6: Human-In-The-Loop Validation
- [ ] **Gap 4:** Snapshot Version Control for mutations/instructions (`@snapshot_before_apply`).
- [ ] **Gap 5:** Interactive Approval Gate for any behavioral instruction edits (`approval_gate.py`).
- [ ] **Gap 15:** Enforced LLM Confidence Origins (Stripping locally hardcoded thresholds).
- [ ] **Gap 17:** Pre-mutation local regression test suite constraints (`RegressionRunner`).

---

## 📊 Definition of Done

Each module is complete **only** when accompanied by its respective automated Unit/Integration test as defined strictly within the `SYSTEM_PROMPT.md` file.

> **Note**: Do not mark any of the items in this manifest as `[x]` checked until the required test actively passes on Windows 10/11 environments.
