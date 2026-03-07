import aiosqlite
import json
import time
from typing import Dict, List, Any, Optional

DB_PATH = "jarvis_state.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT,
                result TEXT,
                error TEXT,
                execution_time REAL,
                timestamp REAL,
                metadata TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp REAL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                source TEXT,
                level TEXT,
                message TEXT,
                data TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS confidence_records (
                trace_id TEXT PRIMARY KEY,
                predicted_confidence REAL NOT NULL,
                actual_success BOOLEAN NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calibration_profiles (
                profile_id TEXT PRIMARY KEY,
                temperature_scalar REAL NOT NULL,
                brier_score REAL,
                records_used INTEGER NOT NULL,
                fitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prompt_variants (
                variant_id TEXT PRIMARY KEY,
                prompt_text TEXT NOT NULL,
                generation INTEGER NOT NULL,
                parent_a_id TEXT,
                parent_b_id TEXT,
                mutations_generated INTEGER DEFAULT 0,
                mutations_promoted INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phase 15 - Identity Checkpointing
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                parent_id TEXT REFERENCES checkpoints(id),
                label TEXT NOT NULL,
                trigger TEXT NOT NULL CHECK (trigger IN ('scheduled', 'pre_mutation', 'post_distillation', 'manual', 'anomaly_detected')),
                change_narrative TEXT,
                health_snapshot_json TEXT NOT NULL,
                instructions_path TEXT,
                calibration_params_path TEXT,
                skill_library_path TEXT,
                classifier_weights_path TEXT,
                vector_store_snapshot_path TEXT,
                meta_learning_policy_path TEXT,
                failure_predictor_path TEXT,
                sft_dataset_hash TEXT,
                created_at_timestamp REAL NOT NULL,
                created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at ON checkpoints(created_at_timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_trigger ON checkpoints(trigger);
            CREATE INDEX IF NOT EXISTS idx_checkpoints_parent_id ON checkpoints(parent_id);

            CREATE TABLE IF NOT EXISTS checkpoint_diffs (
                id TEXT PRIMARY KEY,
                checkpoint_a_id TEXT NOT NULL REFERENCES checkpoints(id),
                checkpoint_b_id TEXT NOT NULL REFERENCES checkpoints(id),
                semantic_distance INTEGER CHECK (semantic_distance >= 0 AND semantic_distance <= 540),
                instruction_delta_json TEXT,
                calibration_delta_json TEXT,
                skill_delta_json TEXT,
                classifier_drift REAL CHECK (classifier_drift >= 0.0 AND classifier_drift <= 1.0),
                narrative TEXT,
                created_at TEXT NOT NULL,
                created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_diffs_checkpoints ON checkpoint_diffs(checkpoint_a_id, checkpoint_b_id);
            CREATE INDEX IF NOT EXISTS idx_diffs_created_at ON checkpoint_diffs(created_at DESC);

            CREATE TABLE IF NOT EXISTS value_drift_events (
                id TEXT PRIMARY KEY,
                checkpoint_id TEXT NOT NULL REFERENCES checkpoints(id),
                alert_level TEXT NOT NULL CHECK (alert_level IN ('WARN', 'ALERT')),
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                threshold REAL NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_drift_checkpoint_id ON value_drift_events(checkpoint_id);
            CREATE INDEX IF NOT EXISTS idx_drift_alert_level ON value_drift_events(alert_level);
            CREATE INDEX IF NOT EXISTS idx_drift_created_at ON value_drift_events(created_at DESC);
        """)
        
        await db.commit()

async def save_task(task_id: str, status: str, result: Optional[Any], error: Optional[str], execution_time: float, timestamp: float, metadata: Dict[str, Any]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO tasks (task_id, status, result, error, execution_time, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, status, json.dumps(result) if result else None, error, execution_time, timestamp, json.dumps(metadata))
        )
        await db.commit()

async def get_all_tasks(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
        rows = await cursor.fetchall()
        
        return [
            {
                "task_id": row["task_id"],
                "status": row["status"],
                "result": json.loads(row["result"]) if row["result"] else None,
                "error": row["error"],
                "execution_time": row["execution_time"],
                "timestamp": row["timestamp"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            }
            for row in rows
        ]

async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        
        if not row:
            return None
            
        return {
            "task_id": row["task_id"],
            "status": row["status"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"],
            "execution_time": row["execution_time"],
            "timestamp": row["timestamp"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
        }
