"""
Database migrations for Fifth Chapter: Identity

Creates tables for behavioral checkpoints, diffs, and drift events.
"""

MIGRATIONS = [
    # Migration 1: Create checkpoints table
    """
    CREATE TABLE IF NOT EXISTS checkpoints (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        parent_id TEXT REFERENCES checkpoints(id),
        label TEXT NOT NULL,
        trigger TEXT NOT NULL CHECK (trigger IN ('scheduled', 'pre_mutation', 'post_distillation', 'manual', 'anomaly_detected')),
        change_narrative TEXT,
        health_snapshot_json TEXT NOT NULL,
        
        -- The 8 identity component paths
        instructions_path TEXT,
        calibration_params_path TEXT,
        skill_library_path TEXT,
        classifier_weights_path TEXT,
        vector_store_snapshot_path TEXT,
        meta_learning_policy_path TEXT,
        failure_predictor_path TEXT,
        
        -- Dataset signature (hash, not full dataset)
        sft_dataset_hash TEXT,
        
        -- Timestamp for range queries
        created_at_timestamp REAL NOT NULL,
        
        -- Metadata
        created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at_timestamp DESC);
    CREATE INDEX idx_checkpoints_trigger ON checkpoints(trigger);
    CREATE INDEX idx_checkpoints_parent_id ON checkpoints(parent_id);
    """,
    
    # Migration 2: Create checkpoint_diffs table
    """
    CREATE TABLE IF NOT EXISTS checkpoint_diffs (
        id TEXT PRIMARY KEY,
        checkpoint_a_id TEXT NOT NULL REFERENCES checkpoints(id),
        checkpoint_b_id TEXT NOT NULL REFERENCES checkpoints(id),
        
        -- Semantic distance (Hamming on 540-record regression suite)
        semantic_distance INTEGER CHECK (semantic_distance >= 0 AND semantic_distance <= 540),
        
        -- Component deltas (stored as JSON)
        instruction_delta_json TEXT,
        calibration_delta_json TEXT,
        skill_delta_json TEXT,
        
        -- Classifier drift (cosine distance 0-1)
        classifier_drift REAL CHECK (classifier_drift >= 0.0 AND classifier_drift <= 1.0),
        
        -- LLM-generated narrative
        narrative TEXT,
        
        -- Metadata
        created_at TEXT NOT NULL,
        created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_diffs_checkpoints ON checkpoint_diffs(checkpoint_a_id, checkpoint_b_id);
    CREATE INDEX idx_diffs_created_at ON checkpoint_diffs(created_at DESC);
    """,
    
    # Migration 3: Create value_drift_events table
    """
    CREATE TABLE IF NOT EXISTS value_drift_events (
        id TEXT PRIMARY KEY,
        checkpoint_id TEXT NOT NULL REFERENCES checkpoints(id),
        
        -- Alert severity
        alert_level TEXT NOT NULL CHECK (alert_level IN ('WARN', 'ALERT')),
        
        -- Which metric triggered
        metric_name TEXT NOT NULL,
        
        -- Actual value and threshold
        metric_value REAL NOT NULL,
        threshold REAL NOT NULL,
        
        -- Description
        description TEXT,
        
        -- Metadata
        created_at TEXT NOT NULL,
        created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_drift_checkpoint_id ON value_drift_events(checkpoint_id);
    CREATE INDEX idx_drift_alert_level ON value_drift_events(alert_level);
    CREATE INDEX idx_drift_created_at ON value_drift_events(created_at DESC);
    """,
]


async def apply_migrations(db):
    """Apply all migrations to the database."""
    for i, migration in enumerate(MIGRATIONS, 1):
        try:
            await db.execute(migration)
            print(f"✓ Migration {i} applied successfully")
        except Exception as e:
            print(f"✗ Migration {i} failed: {e}")
            raise


if __name__ == "__main__":
    # Test migrations (for development)
    import asyncio
    import aiosqlite
    
    async def test():
        async with aiosqlite.connect(":memory:") as db:
            await apply_migrations(db)
            # Verify tables created
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()
            print(f"\nCreated tables: {[t[0] for t in tables]}")
    
    asyncio.run(test())
