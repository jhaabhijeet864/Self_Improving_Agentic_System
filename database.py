"""
Database Manager for Jarvis-OS
Uses aiosqlite to persist Tasks, Logs, and Memory across process restarts.
"""
import aiosqlite
import json
import logging
from typing import Any, Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class JarvisDatabase:
    def __init__(self, db_path: str = "jarvis_state.sqlite"):
        self.db_path = db_path
        
    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp REAL,
                    ttl REAL,
                    priority INTEGER
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT,
                    result TEXT,
                    error TEXT,
                    execution_time REAL,
                    timestamp REAL,
                    metadata TEXT
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    timestamp REAL,
                    level TEXT,
                    message TEXT,
                    metrics TEXT
                )
            ''')
            await db.commit()
            logger.info(f"Initialized SQLite database at {self.db_path}")

    # --- Memory Operations ---
    async def set_memory(self, key: str, value: Any, timestamp: float, ttl: Optional[float] = None, priority: int = 0):
        async with aiosqlite.connect(self.db_path) as db:
            val_str = json.dumps(value)
            await db.execute(
                'INSERT OR REPLACE INTO memory (key, value, timestamp, ttl, priority) VALUES (?, ?, ?, ?, ?)',
                (key, val_str, timestamp, ttl, priority)
            )
            await db.commit()

    async def get_memory(self, key: str) -> Optional[Any]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT value, timestamp, ttl FROM memory WHERE key = ?', (key,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    val_str, ts, ttl = row
                    # Optional: handle ttl expiration here or let memory manager do it
                    return json.loads(val_str)
                return None
                
    async def delete_memory(self, key: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM memory WHERE key = ?', (key,))
            await db.commit()
            
    async def clear_memory(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM memory')
            await db.commit()

    async def get_memory_size(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM memory') as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    # --- Task Operations ---
    async def save_task(self, task_result: Any):
        # task_result is a TaskResult object
        async with aiosqlite.connect(self.db_path) as db:
            result_str = json.dumps(task_result.result) if task_result.result is not None else None
            metadata_str = json.dumps(task_result.metadata) if task_result.metadata else "{}"
            await db.execute(
                '''INSERT OR REPLACE INTO tasks 
                   (task_id, status, result, error, execution_time, timestamp, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    task_result.task_id, 
                    task_result.status.value, 
                    result_str, 
                    task_result.error, 
                    task_result.execution_time, 
                    task_result.timestamp, 
                    metadata_str
                )
            )
            await db.commit()

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "task_id": row[0],
                        "status": row[1],
                        "result": json.loads(row[2]) if row[2] else None,
                        "error": row[3],
                        "execution_time": row[4],
                        "timestamp": row[5],
                        "metadata": json.loads(row[6]) if row[6] else {}
                    }
                return None

    async def get_all_tasks(self) -> Dict[str, Any]:
        tasks = {}
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM tasks') as cursor:
                async for row in cursor:
                    from executor import TaskResult, TaskStatus
                    tasks[row[0]] = TaskResult(
                        task_id=row[0],
                        status=TaskStatus(row[1]),
                        result=json.loads(row[2]) if row[2] else None,
                        error=row[3],
                        execution_time=row[4],
                        timestamp=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
        return tasks

    # --- Log Operations ---
    async def save_log(self, log_entry: Any):
        # log_entry is a LogEntry object
        async with aiosqlite.connect(self.db_path) as db:
            metrics_str = json.dumps(log_entry.metrics) if log_entry.metrics else "{}"
            await db.execute(
                'INSERT INTO logs (task_id, timestamp, level, message, metrics) VALUES (?, ?, ?, ?, ?)',
                (log_entry.task_id, log_entry.timestamp, log_entry.level, log_entry.message, metrics_str)
            )
            await db.commit()

    async def get_all_logs(self) -> List[Any]:
        logs = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT task_id, timestamp, level, message, metrics FROM logs ORDER BY timestamp ASC') as cursor:
                async for row in cursor:
                    from autopsy import LogEntry
                    logs.append(LogEntry(
                        task_id=row[0],
                        timestamp=row[1],
                        level=row[2],
                        message=row[3],
                        metrics=json.loads(row[4]) if row[4] else {}
                    ))
        return logs
