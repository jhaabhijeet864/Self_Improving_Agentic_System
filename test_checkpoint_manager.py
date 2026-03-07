"""
Test Suite: CheckpointManager (Phase 1 - Identity)

Comprehensive tests for checkpoint creation, storage, retrieval, and linked list traversal.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock

from checkpoint_manager import (
    CheckpointManager,
    BehavioralCheckpoint,
    SystemHealthSnapshot,
    CheckpointTrigger,
)


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.checkpoints = {}
        self.next_id = 0
    
    async def fetch(self, query: str, params=None):
        """Mock fetch query."""
        if "ORDER BY created_at DESC LIMIT 1" in query:
            # Get latest checkpoint
            if not self.checkpoints:
                return []
            latest = sorted(
                self.checkpoints.values(),
                key=lambda x: x['created_at'],
                reverse=True
            )[0]
            return [latest]
        
        if "WHERE id = ?" in query:
            # Get by ID
            checkpoint_id = params[0] if params else None
            if checkpoint_id in self.checkpoints:
                return [self.checkpoints[checkpoint_id]]
            return []
        
        if "ORDER BY created_at DESC" in query:
            # List checkpoints
            limit = params[0] if params else 100
            offset = params[1] if len(params) > 1 else 0
            sorted_ckpts = sorted(
                self.checkpoints.values(),
                key=lambda x: x['created_at'],
                reverse=True
            )
            return sorted_ckpts[offset:offset+limit]
        
        return []
    
    async def execute(self, query: str, params=None):
        """Mock execute (for INSERT, UPDATE, DELETE)."""
        if "INSERT INTO checkpoints" in query:
            # Store checkpoint
            checkpoint_id = params[0] if params else f"ckpt-{self.next_id}"
            self.next_id += 1
            self.checkpoints[checkpoint_id] = {
                'id': checkpoint_id,
                'created_at': params[1] if len(params) > 1 else datetime.now().isoformat(),
                'parent_id': params[2] if len(params) > 2 else None,
                'label': params[3] if len(params) > 3 else '',
                'trigger': params[4] if len(params) > 4 else 'manual',
                'change_narrative': params[5] if len(params) > 5 else '',
                'health_snapshot_json': params[6] if len(params) > 6 else '{}',
                'instructions_path': params[7] if len(params) > 7 else '',
                'calibration_params_path': params[8] if len(params) > 8 else '',
                'skill_library_path': params[9] if len(params) > 9 else '',
                'classifier_weights_path': params[10] if len(params) > 10 else '',
                'vector_store_snapshot_path': params[11] if len(params) > 11 else '',
                'meta_learning_policy_path': params[12] if len(params) > 12 else '',
                'failure_predictor_path': params[13] if len(params) > 13 else '',
                'sft_dataset_hash': params[14] if len(params) > 14 else '',
                'created_at_timestamp': params[15] if len(params) > 15 else 0.0,
            }


@pytest.mark.asyncio
async def test_create_checkpoint_captures_all_eight_components():
    """Test that checkpoint creation captures all 8 components."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        # Create mock component files
        components = {}
        for comp in ['instructions', 'calibration_params', 'skill_library',
                     'classifier_weights', 'vector_store', 'meta_learning_policy',
                     'failure_predictor']:
            comp_file = artifact_root / f"{comp}.txt"
            comp_file.write_text(f"Mock {comp} data")
            components[comp] = comp_file
        
        health = SystemHealthSnapshot(
            calibration_error=0.05,
            dataset_coverage=0.95,
            skill_utilization=0.80,
            instruction_debt_days=5,
            failure_prediction_staleness_days=2,
        )
        
        # Create checkpoint
        checkpoint = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            label="test-checkpoint",
            health_snapshot=health,
            identity_components=components,
            sft_dataset_hash="mock-hash-123",
        )
        
        # Assertions
        assert checkpoint.checkpoint_id is not None
        assert checkpoint.label == "test-checkpoint"
        assert checkpoint.trigger == CheckpointTrigger.SCHEDULED
        assert checkpoint.health_snapshot.calibration_error == 0.05
        assert checkpoint.sft_dataset_hash == "mock-hash-123"
        assert checkpoint.instructions_path.exists()
        assert checkpoint.calibration_params_path.exists()
        assert checkpoint.skill_library_path.exists()


@pytest.mark.asyncio
async def test_checkpoint_creation_with_different_triggers():
    """Test that checkpoint creation works with all trigger types."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        triggers = [
            CheckpointTrigger.SCHEDULED,
            CheckpointTrigger.PRE_MUTATION,
            CheckpointTrigger.POST_DISTILLATION,
            CheckpointTrigger.MANUAL,
            CheckpointTrigger.ANOMALY_DETECTED,
        ]
        
        for trigger in triggers:
            checkpoint = await manager.create_checkpoint(
                trigger=trigger,
                label=f"test-{trigger.value}",
            )
            
            assert checkpoint.trigger == trigger
            assert checkpoint.label == f"test-{trigger.value}"
            # Verify stored in database
            assert checkpoint.checkpoint_id in db.checkpoints


@pytest.mark.asyncio
async def test_get_checkpoint_by_id():
    """Test retrieving a checkpoint by ID."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        # Create checkpoint
        created = await manager.create_checkpoint(
            trigger=CheckpointTrigger.MANUAL,
            label="retrieve-test",
        )
        
        # Retrieve it
        retrieved = await manager.get_checkpoint(created.checkpoint_id)
        
        assert retrieved is not None
        assert retrieved.checkpoint_id == created.checkpoint_id
        assert retrieved.label == "retrieve-test"


@pytest.mark.asyncio
async def test_list_checkpoints_with_pagination():
    """Test listing checkpoints with limit and offset."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        # Create 20 checkpoints
        for i in range(20):
            await manager.create_checkpoint(
                trigger=CheckpointTrigger.SCHEDULED,
                label=f"checkpoint-{i}",
            )
        
        # List with limit
        page1 = await manager.list_checkpoints(limit=10, offset=0)
        assert len(page1) == 10
        
        # Get next page
        page2 = await manager.list_checkpoints(limit=10, offset=10)
        assert len(page2) == 10
        
        # Verify no overlap
        ids1 = {c.checkpoint_id for c in page1}
        ids2 = {c.checkpoint_id for c in page2}
        assert len(ids1 & ids2) == 0


@pytest.mark.asyncio
async def test_checkpoint_history_linked_list():
    """Test that checkpoints form a linked list with parent_checkpoint_id."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        # Create 3 checkpoints in sequence
        ckpt1 = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            label="first",
        )
        
        ckpt2 = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            label="second",
        )
        
        ckpt3 = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            label="third",
        )
        
        # Verify parent links
        assert ckpt1.parent_checkpoint_id is None  # First checkpoint
        assert ckpt2.parent_checkpoint_id == ckpt1.checkpoint_id
        assert ckpt3.parent_checkpoint_id == ckpt2.checkpoint_id
        
        # Traverse chain backwards
        retrieved_ckpt3 = await manager.get_checkpoint(ckpt3.checkpoint_id)
        assert retrieved_ckpt3.parent_checkpoint_id == ckpt2.checkpoint_id
        
        retrieved_ckpt2 = await manager.get_checkpoint(retrieved_ckpt3.parent_checkpoint_id)
        assert retrieved_ckpt2.parent_checkpoint_id == ckpt1.checkpoint_id


@pytest.mark.asyncio
async def test_auto_generated_checkpoint_label():
    """Test that labels are auto-generated if not provided."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        checkpoint = await manager.create_checkpoint(
            trigger=CheckpointTrigger.SCHEDULED,
            # No label provided
        )
        
        # Should have auto-generated label
        assert checkpoint.label is not None
        assert "checkpoint-" in checkpoint.label
        assert len(checkpoint.label) > 0


@pytest.mark.asyncio
async def test_checkpoint_health_snapshot():
    """Test that health snapshot is properly stored and retrieved."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        health = SystemHealthSnapshot(
            calibration_error=0.12,
            dataset_coverage=0.85,
            skill_utilization=0.60,
            instruction_debt_days=45,
            failure_prediction_staleness_days=8,
        )
        
        checkpoint = await manager.create_checkpoint(
            trigger=CheckpointTrigger.POST_DISTILLATION,
            health_snapshot=health,
        )
        
        # Verify health snapshot stored
        assert checkpoint.health_snapshot.calibration_error == 0.12
        assert checkpoint.health_snapshot.dataset_coverage == 0.85
        assert checkpoint.health_snapshot.instruction_debt_days == 45


@pytest.mark.asyncio
async def test_checkpoint_with_missing_components():
    """Test checkpoint creation when some components are missing."""
    with TemporaryDirectory() as tmpdir:
        db = MockDatabase()
        artifact_root = Path(tmpdir)
        manager = CheckpointManager(db, artifact_root)
        
        # Create with only some components
        components = {
            'instructions': Path(tmpdir) / 'instructions.txt',
            'classifier_weights': Path(tmpdir) / 'weights.pkl',
        }
        components['instructions'].write_text("test")
        components['classifier_weights'].write_text("test")
        
        checkpoint = await manager.create_checkpoint(
            trigger=CheckpointTrigger.MANUAL,
            identity_components=components,
        )
        
        # Should still create checkpoint with placeholders for missing components
        assert checkpoint.checkpoint_id is not None
        assert checkpoint.instructions_path.exists()
        assert checkpoint.classifier_weights_path.exists()


@pytest.mark.asyncio
async def test_checkpoint_serialization():
    """Test checkpoint to_dict serialization."""
    checkpoint = BehavioralCheckpoint(
        checkpoint_id="test-123",
        created_at=datetime.now(),
        label="test",
        change_narrative="Test changes",
        instructions_path=Path("/tmp/instructions.txt"),
        calibration_params_path=Path("/tmp/cal.json"),
        skill_library_path=Path("/tmp/skills.pkl"),
        classifier_weights_path=Path("/tmp/weights.pkl"),
        vector_store_snapshot_path=Path("/tmp/vectors.db"),
        meta_learning_policy_path=Path("/tmp/policy.json"),
        failure_predictor_path=Path("/tmp/predictor.pkl"),
        sft_dataset_hash="abc123",
        trigger=CheckpointTrigger.SCHEDULED,
        health_snapshot=SystemHealthSnapshot(
            calibration_error=0.05,
            dataset_coverage=0.90,
            skill_utilization=0.75,
            instruction_debt_days=5,
            failure_prediction_staleness_days=2,
        ),
        parent_checkpoint_id="parent-123",
    )
    
    serialized = checkpoint.to_dict()
    
    assert serialized['checkpoint_id'] == "test-123"
    assert serialized['label'] == "test"
    assert serialized['trigger'] == 'scheduled'
    assert serialized['parent_checkpoint_id'] == "parent-123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
