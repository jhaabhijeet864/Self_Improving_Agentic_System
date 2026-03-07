# JARVIS Self-Improver: Getting Started

**Project Status**: 🚧 IN DEVELOPMENT

Welcome to the **Jarvis Self-Improver** workspace. The framework builds a rigorous QA and learning pipeline for the core voice assistant, Jarvis-OS.

---

## 🚀 Environment Assumptions & Setup

**Core Prerequisites:**
- **OS**: Windows 10/11 (64-bit) (This is an absolute must due to job object sandboxing logic).
- **Python**: 3.10 or higher.
- **Git**: Clone the repository and navigate into `D:\Coding\Projects\Self_Improve\`.

### 1. The Environment Variable Scaffold

The self-improver cannot run without specific configuration pointers. Create an `.env` file in the root directory and ensure the variables match the specifications seen in `SYSTEM_PROMPT.md`.

```bash
# Example .env Configuration
JARVIS_WORKSPACE=D:\Coding\Projects\Self_Improve\workspace
JARVIS_ADMIN_PASSWORD_HASH=<bcrypt_hash_placeholder>

# Inference Layer Config
CLOUD_LLM_PROVIDER=gemini # or "openai"
GEMINI_API_KEY=<your_gemini_key>
OPENAI_API_KEY=<your_openai_key>
```

> **Generating your Admin Pass Hash:**  
> Run the following python command to secure your admin API operations:
> `python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))"`

### 2. Pre-Requisite Validations

Because the project communicates over IPC with the external Jarvis Voice agent and stores long-term concepts:
- **Database**: The project auto-creates `jarvis_data.sqlite` on its first run.
- **IPC Port**: Default is `ws://127.0.0.1:9999/jarvis-events`
- **Dashboard API**: Default port 8000.

---

## 🛠️ Bootstrapping (The Absolute First Step)

Before you dive into complex self-improving logic, **you must execute Gap 0**.

### Running the System Auditor
The original code scaffold was padded by LLMs. To begin engaging with this project cleanly, an `audit.py` file must be generated (per Gap 0) and run.

```bash
# Run the audit script and locate the BLOATED and STUB files.
python audit.py
```

Only files that report as **HEALTHY** are production safe. If an executable `.py` script returns **BLOATED**, rewrite its functional core cleanly and rerun the auditor.

---

## 📚 Moving Forward

Take the 20 gaps listed in `PROJECT_MANIFEST.md` completely in logical order.

1. Create a branch for the gap (e.g., `gap-1-llm-critique`).
2. Write the core unit tests mandated by `SYSTEM_PROMPT.md` for that gap.
3. Write the implementation code utilizing pure `asyncio` and typed `Pydantic` structures.
4. Pass the test, log the completion, and move forward.

> **Caution:** Do not use `threading.Event`, arbitrary `time.sleep()`, or generic `dict` tracking. 

For full architectural blueprints, refer strictly to `SYSTEM_PROMPT.md`. Let's build a genuinely sentient workflow optimizer!
