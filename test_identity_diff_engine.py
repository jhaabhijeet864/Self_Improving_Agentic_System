"""
Test Suite: IdentityDiffEngine (Phase 2 - Identity)

Comprehensive tests for generating diffs between semantic checkpoints.
"""

import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock

from checkpoint_manager import CheckpointManager, BehavioralCheckpoint, CheckpointTrigger, SystemHealthSnapshot
from identity_diff_engine import IdentityDiffEngine, BehavioralDiff

class MockDatabaseDiff:
    """Mock database for testing IdentityDiffEngine."""
    
    def __init__(self):
        self.checkpoints = {}
        self.diffs = {}
        self.next_id = 0
    
    async def fetch(self, query: str, params=None):
        if "FROM checkpoints" in query:
            checkpoint_id = params[0] if params else None
            # Return full dict mapping exactly to what CheckpointManager expects
            if checkpoint_id in self.checkpoints:
                return [self.checkpoints[checkpoint_id]]
            return []
            
        if "FROM checkpoint_diffs" in query:
            ch_a = params[0]
            ch_b = params[1]
            # Match existing diffs
            for d in self.diffs.values():
                if d['checkpoint_a_id'] == ch_a and d['checkpoint_b_id'] == ch_b:
                    return [d]
            return []
        
        return []
    
    async def execute(self, query: str, params=None):
        if "INSERT INTO checkpoints" in query:
            checkpoint_id = params[0]
            self.checkpoints[checkpoint_id] = {
                'id': checkpoint_id,
                'created_at': params[1],
                'parent_id': params[2],
                'label': params[3],
                'trigger': params[4],
                'change_narrative': params[5],
                'health_snapshot_json': params[6],
                'instructions_path': params[7],
                'calibration_params_path': params[8],
                'skill_library_path': params[9],
                'classifier_weights_path': params[10],
                'vector_store_snapshot_path': params[11],
                'meta_learning_policy_path': params[12],
                'failure_predictor_path': params[13],
                'sft_dataset_hash': params[14]
            }
        elif "INSERT INTO checkpoint_diffs" in query:
            diff_id = params[0]
            self.diffs[diff_id] = {
                'id': diff_id,
                'checkpoint_a_id': params[1],
                'checkpoint_b_id': params[2],
                'semantic_distance': params[3],
                'instruction_delta_json': params[4],
                'calibration_delta_json': params[5],
                'skill_delta_json': params[6],
                'classifier_drift': params[7],
                'narrative': params[8],
                'created_at': params[9]
            }

@pytest.mark.asyncio
async def test_identity_diff_engine_computes_deltas():
    with TemporaryDirectory() as tmpdir:
        db = MockDatabaseDiff()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        # Create Checkpoint A components
        components_a = {}
        comp_a_dir = artifact_root / 'c_a'
        comp_a_dir.mkdir()
        components_a['instructions'] = comp_a_dir / "instructions.txt"
        components_a['instructions'].write_text("Hello World\\nVersion 1")
        
        components_a['calibration_params'] = comp_a_dir / "cal.json"
        components_a['calibration_params'].write_text(json.dumps({"temp": 0.5}))
        
        # Checkpoint A
        ckpt_a = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            label="a",
            identity_components=components_a
        )
        
        # Create Checkpoint B components
        components_b = {}
        comp_b_dir = artifact_root / 'c_b'
        comp_b_dir.mkdir()
        components_b['instructions'] = comp_b_dir / "instructions.txt"
        components_b['instructions'].write_text("Hello World\\nVersion 2\\nAdded Line")
        
        components_b['calibration_params'] = comp_b_dir / "cal.json"
        components_b['calibration_params'].write_text(json.dumps({"temp": 0.7, "new_scalar": 1.2}))
        
        ckpt_b = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            label="b",
            identity_components=components_b
        )
        
        engine = IdentityDiffEngine(db, manager)
        
        # Compute Diff
        diff = await engine.compute_diff(ckpt_a.checkpoint_id, ckpt_b.checkpoint_id)
        
        assert diff.semantic_distance > 0
        
        # Instruction Deltas
        assert diff.instruction_delta["changed"] is True
        assert "added_lines" in diff.instruction_delta
        assert diff.instruction_delta["added_lines"] == 2  # Version 2 & Added Line
        
        # Calibration Deltas
        assert diff.calibration_delta["changed"] is True
        assert "new_scalar" in diff.calibration_delta["added_keys"]
        assert "temp" in diff.calibration_delta["modified_keys"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
