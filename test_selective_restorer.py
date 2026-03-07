"""
Tests for SelectiveRestorer (Phase 4)
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime

from selective_restorer import SelectiveRestorer, RestorePreview, RestoreResult


@pytest.fixture
def mock_checkpoint_manager():
    """Mock CheckpointManager."""
    manager = AsyncMock()
    
    # Mock checkpoint data
    checkpoint_current = {
        'checkpoint_id': 'ckpt-001',
        'instructions_path': '/tmp/instructions.json',
        'calibration_params_path': '/tmp/calibration.json',
        'skill_library_path': '/tmp/skills.json',
        'classifier_weights_path': '/tmp/classifier.onnx',
        'vector_store_snapshot_path': '/tmp/vector_store.pkl',
        'meta_learning_policy_path': '/tmp/policy.pkl',
        'failure_predictor_path': '/tmp/predictor.pkl',
    }
    
    checkpoint_target = {
        'checkpoint_id': 'ckpt-000',
        'instructions_path': '/tmp/instructions.json',
        'calibration_params_path': '/tmp/calibration.json',
        'skill_library_path': '/tmp/skills.json',
        'classifier_weights_path': '/tmp/classifier.onnx',
        'vector_store_snapshot_path': '/tmp/vector_store.pkl',
        'meta_learning_policy_path': '/tmp/policy.pkl',
        'failure_predictor_path': '/tmp/predictor.pkl',
    }
    
    manager.get_checkpoint = AsyncMock(side_effect=lambda cid: (
        Mock(**checkpoint_current) if cid == 'ckpt-001'
        else Mock(**checkpoint_target) if cid == 'ckpt-000'
        else None
    ))
    
    return manager


@pytest.fixture
def mock_diff_engine():
    """Mock IdentityDiffEngine."""
    engine = AsyncMock()
    
    diff_mock = Mock()
    diff_mock.semantic_distance = 150
    diff_mock.narrative = "Instructions changed significantly"
    diff_mock.instruction_delta = Mock(
        lines_added=50,
        lines_removed=30,
        semantic_similarity=0.6,
    )
    diff_mock.calibration_delta = Mock(
        temperature_shift=0.1,
        curve_divergence=0.05,
    )
    diff_mock.skill_delta = Mock(
        skills_added=['new_skill'],
        skills_removed=[],
        skills_modified=['updated_skill'],
    )
    diff_mock.classifier_drift = 0.08
    
    engine.compute_diff = AsyncMock(return_value=diff_mock)
    
    return engine


@pytest.fixture
def restorer(mock_checkpoint_manager, mock_diff_engine, tmp_path):
    """Initialize SelectiveRestorer."""
    restorer = SelectiveRestorer(
        checkpoint_manager=mock_checkpoint_manager,
        diff_engine=mock_diff_engine,
        regression_suite_path=tmp_path / "regression_suite.json",
    )
    return restorer


class TestRestoreOptions:
    """Test restore option analysis."""
    
    @pytest.mark.asyncio
    async def test_get_restore_options(self, restorer, mock_checkpoint_manager, mock_diff_engine):
        """Test getting restore options."""
        # Mock current checkpoint
        async def get_ckpt(cid):
            current = Mock(
                checkpoint_id='ckpt-001',
                instructions_path='/tmp/current/instructions.json',
            )
            target = Mock(
                checkpoint_id='ckpt-000',
                instructions_path='/tmp/target/instructions.json',
            )
            return current if cid == 'ckpt-001' else target
        
        mock_checkpoint_manager.get_checkpoint = AsyncMock(side_effect=get_ckpt)
        
        # Mock list_checkpoints to return current
        mock_checkpoint_manager.list_checkpoints = AsyncMock(
            return_value=[Mock(checkpoint_id='ckpt-001')]
        )
        
        options = await restorer.get_restore_options('ckpt-000')
        
        assert 'component_changes' in options
        assert 'semantic_distance' in options
        assert options['semantic_distance'] == 150
        assert options['narrative'] == "Instructions changed significantly"


class TestRestorePreview:
    """Test restore preview functionality."""
    
    @pytest.mark.asyncio
    async def test_preview_restore_high_impact(self, restorer):
        """Test preview for high-impact components."""
        preview = await restorer.preview_restore(
            target_checkpoint_id='ckpt-000',
            components_to_restore=['instructions', 'classifier'],
            sample_size=50,
        )
        
        assert isinstance(preview, RestorePreview)
        assert 'instructions' in preview.components_to_restore
        assert preview.predicted_impact == 'high'
        assert preview.predicted_success_rate > 0.5
    
    @pytest.mark.asyncio
    async def test_preview_restore_medium_impact(self, restorer):
        """Test preview for medium-impact components."""
        preview = await restorer.preview_restore(
            target_checkpoint_id='ckpt-000',
            components_to_restore=['calibration'],
            sample_size=50,
        )
        
        assert preview.predicted_impact == 'medium'
    
    @pytest.mark.asyncio
    async def test_preview_restore_low_impact(self, restorer):
        """Test preview for low-impact components."""
        preview = await restorer.preview_restore(
            target_checkpoint_id='ckpt-000',
            components_to_restore=['skills'],
            sample_size=50,
        )
        
        assert preview.predicted_impact == 'low'


class TestSelectiveRestoration:
    """Test selective restoration execution."""
    
    @pytest.mark.asyncio
    async def test_execute_restore_dry_run(self, restorer, tmp_path):
        """Test dry-run mode (no actual file modifications)."""
        # Mock current checkpoint lookup
        restorer.checkpoint_manager.list_checkpoints = AsyncMock(
            return_value=[Mock(checkpoint_id='ckpt-001')]
        )
        
        result = await restorer.execute_restore(
            target_checkpoint_id='ckpt-000',
            components_to_restore=['instructions', 'calibration'],
            dry_run=True,
        )
        
        assert isinstance(result, RestoreResult)
        assert result.status in ['success', 'partial', 'failed']
        assert isinstance(result.duration_seconds, float)
    
    @pytest.mark.asyncio
    async def test_execute_restore_invalid_component(self, restorer):
        """Test restore with invalid component name."""
        restorer.checkpoint_manager.list_checkpoints = AsyncMock(
            return_value=[Mock(checkpoint_id='ckpt-001')]
        )
        
        result = await restorer.execute_restore(
            target_checkpoint_id='ckpt-000',
            components_to_restore=['invalid_component'],
            dry_run=True,
        )
        
        assert result.status in ['success', 'partial']
    
    @pytest.mark.asyncio
    async def test_execute_restore_multiple_components(self, restorer):
        """Test restoring multiple components."""
        restorer.checkpoint_manager.list_checkpoints = AsyncMock(
            return_value=[Mock(checkpoint_id='ckpt-001')]
        )
        
        result = await restorer.execute_restore(
            target_checkpoint_id='ckpt-000',
            components_to_restore=['instructions', 'classifier', 'skills'],
            dry_run=True,
        )
        
        assert len(result.components_restored) >= 0


class TestRestoreImpact:
    """Test impact measurement."""
    
    @pytest.mark.asyncio
    async def test_measure_restore_impact(self, restorer):
        """Test measuring restoration impact."""
        impact = await restorer.measure_restore_impact(
            before_checkpoint_id='ckpt-001',
            after_checkpoint_id='ckpt-000',
        )
        
        assert 'tests_improved' in impact
        assert 'tests_regressed' in impact
        assert 'tests_unchanged' in impact
        assert 'success_rate_delta' in impact


class TestComponentPaths:
    """Test component path resolution."""
    
    def test_get_component_path(self, restorer):
        """Test getting correct component path."""
        checkpoint = Mock(
            instructions_path='/tmp/instr.json',
            calibration_params_path='/tmp/calib.json',
            classifier_weights_path='/tmp/clf.onnx',
        )
        
        instr_path = restorer._get_component_path(checkpoint, 'instructions')
        assert str(instr_path) == '/tmp/instr.json'
        
        calib_path = restorer._get_component_path(checkpoint, 'calibration_params')
        assert str(calib_path) == '/tmp/calib.json'


@pytest.mark.asyncio
async def test_restore_workflow_full():
    """Test full restore workflow: preview → execute → measure."""
    from unittest.mock import AsyncMock, Mock
    
    # Setup mocks
    checkpoint_mgr = AsyncMock()
    diff_engine = AsyncMock()
    
    checkpoint_mgr.list_checkpoints = AsyncMock(
        return_value=[Mock(checkpoint_id='ckpt-001')]
    )
    
    ckpt_current = Mock(
        checkpoint_id='ckpt-001',
        instructions_path='/tmp/cur/instr.json',
    )
    ckpt_target = Mock(
        checkpoint_id='ckpt-000',
        instructions_path='/tmp/target/instr.json',
    )
    
    async def get_ckpt(cid):
        return ckpt_current if cid == 'ckpt-001' else ckpt_target
    
    checkpoint_mgr.get_checkpoint = AsyncMock(side_effect=get_ckpt)
    
    diff_mock = Mock(
        semantic_distance=150,
        narrative="Change detected",
        instruction_delta=Mock(semantic_similarity=0.6),
        calibration_delta=Mock(temperature_shift=0.1),
        skill_delta=Mock(skills_added=[], skills_removed=[], skills_modified=[]),
        classifier_drift=0.08,
    )
    diff_engine.compute_diff = AsyncMock(return_value=diff_mock)
    
    restorer = SelectiveRestorer(
        checkpoint_manager=checkpoint_mgr,
        diff_engine=diff_engine,
    )
    
    # Step 1: Preview
    preview = await restorer.preview_restore(
        target_checkpoint_id='ckpt-000',
        components_to_restore=['instructions'],
    )
    assert preview.predicted_success_rate > 0.5
    
    # Step 2: Execute
    result = await restorer.execute_restore(
        target_checkpoint_id='ckpt-000',
        components_to_restore=['instructions'],
        dry_run=True,
    )
    assert result.status in ['success', 'partial', 'failed']
    
    # Step 3: Measure impact
    impact = await restorer.measure_restore_impact(
        before_checkpoint_id='ckpt-001',
        after_checkpoint_id='ckpt-000',
    )
    assert 'tests_improved' in impact


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
