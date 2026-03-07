# 🤖 JARVIS-OS & Self-Improver: Index & Quick Reference

**Status**: 🚧 ACTIVE DEVELOPMENT - Working through 20-Gap Implementation Plan

---

## 📂 Project Navigation

This repository contains the complementary **Jarvis Self-Improver** system alongside the foundation of the Jarvis-OS. The codebase is currently undergoing a massive refactor to replace generated stubs with production-ready `asyncio` code.

### 📖 Documentation Directory

| Document | Purpose |
|----------|---------|
| **[SYSTEM_PROMPT.md](SYSTEM_PROMPT.md)** | **The True North Star.** Start here. Defines the architecture, constraints, and the 20 actionable gaps to fix. |
| **[README_FULL.md](README_FULL.md)** | Architecture overview, vision, and high-level component explanations. |
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Steps for developers to set up the workspace, requirements, and run the mandatory code auditing script. |
| **[PROJECT_MANIFEST.md](PROJECT_MANIFEST.md)** | The definitive checklist and progress tracker for the 20-Gap Roadmap. |

### 🔧 Core Modules (Currently Under Audit & Refactoring)

```
1. executor.py          - Scheduled for pywin32 job object sandboxing (Gap 6)
2. autopsy.py          - Scheduled for explicit error taxonomy and structured data (Gap 10)
3. mutation.py         - Scheduled for Human-in-the-Loop gating and snapshots (Gap 4/5)
4. memory_manager.py   - Scheduled for ChromaDB Vector migration (Gap 7)
5. fast_router.py      - Scheduled for local sentence-transformers NLP classifier (Gap 2)
6. structured_logger.py - Scheduled for source telemetry enhancements (Gap 14)
7. jarvis_os.py        - The main orchestrator loop
```

### 🚧 Priority Action: Mandatory Audit

Before you begin modifying or executing core modules, you **must run** the project audit script:

```bash
# Verify actual unique code line counts and identify bloated files (Gap 0)
python audit.py
```
*(If `audit.py` does not exist yet, creating it is your absolute first priority).*

---

## 🚀 Quick Reference: Core Workflows

### 1. Self-Critique Loop (Gap 1)
Instead of static heuristics, we utilize an LLM instance (`gemini` or `openai`) to critically analyze `SessionReport` records and generate structurally parsed JSON `CritiqueResults` indicating root causes and proposed fixes.

### 2. Human Approval Gate (Gap 5)
Mutations and instruction changes are **never** auto-applied based on threshold logic. An `ApprovalRequest` must be acknowledged by a human. If delayed beyond the timeout, the request is discarded.

### 3. IPC Communication (Gap 3)
Jarvis Voice Agent and Jarvis Self-Improver are isolated processes. They speak to each other via a `ws://127.0.0.1:9999/jarvis-events` websocket connection passing Pydantic models.

### 4. Async Precision (Gap 13)
This is an `asyncio` domain. Standard `time.sleep()`, `threading.Event`, or blocking IO must be relegated to async equivalents or `run_in_executor` wrap calls.

---

> **Note to Contributors:** Do not trust legacy line counts or "production-ready" badges. Everything must be validated through the `audit.py` framework and adhere to the Non-Negotiable Engineering Rules outlined in `SYSTEM_PROMPT.md`.
