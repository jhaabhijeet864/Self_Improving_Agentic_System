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
