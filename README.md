# 🧠 Jarvis Self-Improver: Autonomous AI Architecture

![Jarvis-OS Version](https://img.shields.io/badge/version-1.0.0--alpha-orange.svg)
![Status](https://img.shields.io/badge/status-in_development-yellow.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)
![Architecture](https://img.shields.io/badge/architecture-asyncio--driven-blueviolet.svg)

> **Vision**: The Jarvis Self-Improver is a complementary system to the Jarvis-OS voice-activated Windows assistant. Just as Git complements the Linux kernel, the Self-Improver observes the voice agent's interactions, finds patterns in failures and slowdowns, and proposes concrete updates to the agent's routing rules and instructions.

---

## 📖 Table of Contents
1. [Executive Summary & Vision](#executive-summary--vision)
2. [Project Context](#project-context)
3. [Non-Negotiable Engineering Rules](#non-negotiable-engineering-rules)
4. [Deep-Dive Architecture](#deep-dive-architecture)
5. [The Self-Improvement Loop](#the-self-improvement-loop)
6. [Roadmap & 20-Gap Implementation Plan](#roadmap--20-gap-implementation-plan)

---

## 🌟 Executive Summary & Vision

The **Jarvis Self-Improver** is an autonomous QA and learning infrastructure that sits alongside the primary Jarvis voice agent. It is NOT the voice agent itself. Instead, it is the engine that makes the voice agent measurably better over time. 

Most AI agents execute a prompt and stop. The Self-Improver introduces a continuous feedback loop: it intelligently analyzes logs, critiques failures using an LLM, identifies bottlenecks via autopsy, and rewrites its own operational parameters (instructions, rules, memory) dynamically, but always with a **Human-in-the-Loop** safety gate.

---

## 🎯 Project Context

The two projects (Jarvis-OS and Jarvis Self-Improver) communicate over a defined `JarvisEvent` schema via a local WebSocket or Python named pipe. 

**Current State (Action Required):**
The codebase originally contained repetitive boilerplate and bloated line counts. The first step in engaging with this repository is to run the mandatory **Code Audit**. The code is being actively refactored to replace stub heuristics with real LLM reasoning, async concurrency, and local SQLite persistence.

---

## 🛡️ Non-Negotiable Engineering Rules

1. **Audit Before You Build:** Never build on bloated or undefined code. Run `audit.py` first.
2. **No Fabricated Metrics:** Never hardcode confidence scores. Metrics must come from real LLM outputs or regression tests.
3. **Async Discipline:** Use `asyncio` exclusively. No `threading.Event.wait()` inside coroutines.
4. **Every External Call Is Fallible:** Wrap API calls in `try/except` with exponential backoff.
5. **Human-in-the-Loop Is Sacred:** No mutation (instruction update) is applied without explicit human approval.
6. **Every Mutation Gets a Snapshot:** Version control all self-improvements for easy rollback.
7. **Define the Contract First:** Use shared Pydantic models for data interchange between modules.
8. **Windows-First:** Optimized for Windows 10/11 using `pathlib.Path`, job objects, and named pipes.

---

## 🏗️ Deep-Dive Architecture

The system operates on an event-driven model. The lifecycle of the improvement loop works as follows:

-----------+-----------+          +-----------+-----------+
               |                                  ^
               | (JSON Events via IPC)            |
               +----------------------------------+
                                  |
                                  v
                       +-----------------------+      +-------------------+
                       |   Structured Logger   +------>  SQLite Database   |
                       +-----------+-----------+      +---------+---------+
                                   |                            |
                       +-----------v-----------+                |
                       |    Autopsy Analyzer   <----------------+
                       +-----------+-----------+
                                   |
                       +-----------v-----------+      +-------------------+
                       |  Self-Critique Engine +------>     Cloud LLM     |
                       +-----------+-----------+      +-------------------+
                                   |
                       +

### Core Components
1. **Executor Engine (`executor.py`)**: Handles sandboxed execution of testing and background refinement tasks using `win32job` limits.
2. **Fast Router (`fast_router.py`)**: Uses local ML semantic classification (`sentence-transformers`) to route inputs rather than regex.
3. **Memory Manager (`memory_manager.py`)**: ChromaDB-backed persistent vector store for long-term semantic recall.
4. **Autopsy System (`autopsy.py`)**: Periodically sweeps structured logs to identify hidden performance hotspots and categorizes errors via an explicit taxonomy.
5. **Mutation System (`mutation.py`)**: Takes Autopsy reports and works with the Self-Critique Engine to suggest high-confidence instruction updates.
6. **Structured Logger (`structured_logger.py`)**: Logs every micro-action consistently into SQLite.
7. **IPC Bridge (`ipc_bridge.py`)**: Facilitates real-time async communication via WebSockets between the two disparate processes.

---

## 🔄 The Self-Improvement Loop

1. **Collection**: The Voice Agent sends standard JSON execution logs through the IPC Bridge to the `StructuredLogger`.
2. **Analysis**: The `Autopsy` module scans logs to find standard deviations in latency or spikes in typed error categories.
3. **Hypothesis**: The `SelfCritiqueEngine` forwards session reports to a cloud LLM to structurally diagnose failures and generate JSON fixes.
4. **Application**: The `Mutation` engine stages the fixes, requests human approval via the Dashboard API, and enforces a mandatory regression test before altering the agent's live memory.

---

## 📈 Roadmap & 20-Gap Implementation Plan

We are strictly following a **20-Gap Implementation Plan** to transform this framework from boilerplate into a hardened, production-ready system. 

Key gaps being actively addressed (see `PROJECT_MANIFEST.md` for full checklist):
- **Gap 0**: Mandatory code audit via `audit.py`.
- **Gap 1**: Real Cloud LLM Critique Loop instead of heuristic thresholds.
- **Gap 2**: ML-based Semantic Routing vs regex fallbacks.
- **Gap 3**: Local WS/Named-Pipe IPC Bridge.
- **Gap 5**: Human-in-the-Loop UI Approval Gates.
- **Gap 6**: Windows subprocess sandboxing using pywin32 job objects.
- **Gap 7**: Moving long-term memory to a Vector Store (ChromaDB).
- **Gap 9**: Persistent state utilizing async SQLite/SQLAlchemy.
- **Gap 17**: Regression testing pipeline after every mutation.

---

*Built for the future of autonomous systems. Powered by iterative self-improvement and unbreakable constraints.*
