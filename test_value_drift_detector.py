"""
Tests for ValueDriftDetector (Phase 5)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from value_drift_detector import ValueDriftDetector, DriftAlert


@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[])
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_checkpoint_manager():
    """Mock CheckpointManager."""
    manager = AsyncMock()
    
    origin = Mock(
        checkpoint_id='ckpt-origin',
        instructions_path='/tmp/origin/instructions.json',
        label="Original deployment",
    )
    
    current = Mock(
        checkpoint_id='ckpt-current',
        instructions_path='/tmp/current/instructions.json',
        label="Current state",
    )
    
    async def get_ckpt(cid):
        return origin if cid == 'ckpt-origin' else current if cid == 'ckpt-current' else None
    
    manager.get_checkpoint = AsyncMock(side_effect=get_ckpt)
    
    return manager


@pytest.fixture
def mock_timeline():
    """Mock BehavioralTimeline."""
    timeline = AsyncMock()
    
    segment = Mock(
        checkpoint_a_id='ckpt-prev',
        checkpoint_b_id='ckpt-current',
        semantic_distance=50,
    )
    
    timeline.get_timeline_segments = AsyncMock(return_value=[segment])
    
    return timeline


@pytest.fixture
def detector(mock_db, mock_checkpoint_manager, mock_timeline):
    """Initialize ValueDriftDetector."""
    detector = ValueDriftDetector(
        db=mock_db,
        checkpoint_manager=mock_checkpoint_manager,
        timeline=mock_timeline,
        origin_checkpoint_id='ckpt-origin',
    )
    return detector


class TestDriftDetection:
    """Test basic drift detection."""
    
    @pytest.mark.asyncio
    async def test_check_drift_no_drift(self, detector):
        """Test when no drift is detected."""
        with patch('value_drift_detector.IdentityDiffEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            diff = Mock(
                semantic_distance=50,
                instruction_delta=Mock(semantic_similarity=0.95),
                calibration_delta=Mock(temperature_shift=0.01),
                classifier_drift=0.02,
                skill_delta=Mock(skills_added=[], skills_removed=[], skills_modified=[]),
            )
            mock_engine.compute_diff = AsyncMock(return_value=diff)
            
            alert = await detector.check_drift('ckpt-current')
            
            assert alert is None
    
    @pytest.mark.asyncio
    async def test_check_drift_warning_level(self, detector):
        """Test drift detection at WARNING level."""
        with patch('value_drift_detector.IdentityDiffEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            diff = Mock(
                semantic_distance=120,
                instruction_delta=Mock(semantic_similarity=0.75),
                calibration_delta=Mock(temperature_shift=0.05),
                classifier_drift=0.04,
                skill_delta=Mock(skills_added=[], skills_removed=[], skills_modified=[]),
            )
            mock_engine.compute_diff = AsyncMock(return_value=diff)
            
            alert = await detector.check_drift('ckpt-current')
            
            assert alert is not None
            assert alert.alert_level == "WARN"
            assert alert.metric_name == "semantic_distance_from_origin"
    
    @pytest.mark.asyncio
    async def test_check_drift_alert_level(self, detector):
        """Test drift detection at ALERT level (severe)."""
        with patch('value_drift_detector.IdentityDiffEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            diff = Mock(
                semantic_distance=300,
                instruction_delta=Mock(semantic_similarity=0.5),
                calibration_delta=Mock(temperature_shift=0.15),
                classifier_drift=0.12,
                skill_delta=Mock(skills_added=['new1', 'new2'], skills_removed=[], skills_modified=['mod1']),
            )
            mock_engine.compute_diff = AsyncMock(return_value=diff)
            
            alert = await detector.check_drift('ckpt-current')
            
            assert alert is not None
            assert alert.alert_level == "ALERT"
            assert alert.metric_value == 300


class TestDriftMetrics:
    """Test drift metric calculation."""
    
    @pytest.mark.asyncio
    async def test_get_drift_metrics(self, detector):
        """Test retrieving drift metrics."""
        with patch('value_drift_detector.IdentityDiffEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            diff = Mock(
                semantic_distance=150,
                instruction_delta=Mock(semantic_similarity=0.7),
                calibration_delta=Mock(temperature_shift=0.1),
                classifier_drift=0.08,
                skill_delta=Mock(
                    skills_added=['new_skill'],
                    skills_removed=['old_skill'],
                    skills_modified=['updated_skill'],
                ),
            )
            mock_engine.compute_diff = AsyncMock(return_value=diff)
            
            metrics = await detector.get_drift_metrics('ckpt-current')
            
            assert 'semantic_distance_from_origin' in metrics
            assert metrics['semantic_distance_from_origin'] == 150
            assert metrics['semantic_distance_from_origin_percentage'] == pytest.approx(27.78, rel=0.01)
            assert metrics['instruction_semantic_similarity'] == 0.7
            assert metrics['is_drifting'] is True
    
    @pytest.mark.asyncio
    async def test_drift_metrics_percentage_calculation(self, detector):
        """Test percentage drift calculation."""
        with patch('value_drift_detector.IdentityDiffEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            diff = Mock(
                semantic_distance=270,
                instruction_delta=Mock(semantic_similarity=0.5),
                calibration_delta=Mock(temperature_shift=0.2),
                classifier_drift=0.15,
                skill_delta=Mock(skills_added=[], skills_removed=[], skills_modified=[]),
            )
            mock_engine.compute_diff = AsyncMock(return_value=diff)
            
            metrics = await detector.get_drift_metrics('ckpt-current')
            
            # 270/540 = 0.5 = 50%
            assert metrics['semantic_distance_from_origin_percentage'] == 50.0


class TestSustainedDrift:
    """Test sustained drift detection."""
    
    @pytest.mark.asyncio
    async def test_detect_sustained_drift(self, detector, mock_timeline):
        """Test detection of sustained drift over time."""
        segments = [
            Mock(semantic_distance=30, checkpoint_b_id='ckpt-1'),
            Mock(semantic_distance=60, checkpoint_b_id='ckpt-2'),
            Mock(semantic_distance=90, checkpoint_b_id='ckpt-3'),
            Mock(semantic_distance=120, checkpoint_b_id='ckpt-4'),
        ]
        
        mock_timeline.get_timeline_segments = AsyncMock(return_value=segments)
        
        alert = await detector.detect_sustained_drift(days=7, cumulative_threshold=200)
        
        assert alert is not None
        assert alert.alert_level == "ALERT"
        assert "sustained drift" in alert.description.lower()
    
    @pytest.mark.asyncio
    async def test_no_sustained_drift_under_threshold(self, detector, mock_timeline):
        """Test no sustained drift if below threshold."""
        segments = [
            Mock(semantic_distance=20, checkpoint_b_id='ckpt-1'),
            Mock(semantic_distance=30, checkpoint_b_id='ckpt-2'),
            Mock(semantic_distance=25, checkpoint_b_id='ckpt-3'),
        ]
        
        mock_timeline.get_timeline_segments = AsyncMock(return_value=segments)
        
        alert = await detector.detect_sustained_drift(days=7, cumulative_threshold=300)
        
        assert alert is None


class TestOriginCheckpoint:
    """Test origin checkpoint management."""
    
    @pytest.mark.asyncio
    async def test_set_origin_checkpoint(self, detector, mock_checkpoint_manager):
        """Test setting origin checkpoint."""
        await detector.set_origin_checkpoint('ckpt-origin')
        
        assert detector.origin_checkpoint_id == 'ckpt-origin'
    
    @pytest.mark.asyncio
    async def test_set_invalid_origin_checkpoint(self, detector, mock_checkpoint_manager):
        """Test setting non-existent origin checkpoint."""
        mock_checkpoint_manager.get_checkpoint = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError):
            await detector.set_origin_checkpoint('invalid-ckpt')


class TestAlertHistory:
    """Test alert history retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_alert_history(self, detector, mock_db):
        """Test retrieving alert history."""
        alert_row = {
            'id': 'alert-123',
            'checkpoint_id': 'ckpt-001',
            'alert_level': 'WARN',
            'metric_name': 'semantic_distance',
            'metric_value': 100.0,
            'threshold': 100.0,
            'description': 'Moderate drift detected',
            'created_at': datetime.now().isoformat(),
        }
        
        mock_db.fetch = AsyncMock(return_value=[alert_row])
        
        alerts = await detector.get_alert_history(days=30)
        
        assert len(alerts) == 1
        assert alerts[0].alert_id == 'alert-123'
        assert alerts[0].alert_level == 'WARN'
    
    @pytest.mark.asyncio
    async def test_get_alert_history_filtered_by_level(self, detector, mock_db):
        """Test filtering alert history by level."""
        await detector.get_alert_history(days=30, alert_level='ALERT')
        
        # Verify query includes level filter
        assert mock_db.fetch.called
        call_args = mock_db.fetch.call_args
        assert 'alert_level' in call_args[0][0].lower() or 'ALERT' in str(call_args[1])


class TestAlertStorage:
    """Test alert persistence."""
    
    @pytest.mark.asyncio
    async def test_store_alert(self, detector, mock_db):
        """Test storing alert to database."""
        alert = DriftAlert(
            alert_id='alert-123',
            checkpoint_id='ckpt-001',
            alert_level='WARN',
            metric_name='semantic_distance',
            metric_value=120.0,
            threshold=100.0,
            description='Moderate drift detected',
            created_at=datetime.now(),
        )
        
        await detector.store_alert(alert)
        
        assert mock_db.execute.called
        call_args = mock_db.execute.call_args
        # Verify INSERT statement
        assert 'INSERT' in call_args[0][0]


@pytest.mark.asyncio
async def test_drift_detection_workflow():
    """Test complete drift detection workflow."""
    from unittest.mock import AsyncMock, Mock
    
    # Setup mocks
    db = AsyncMock()
    checkpoint_mgr = AsyncMock()
    timeline = AsyncMock()
    
    checkpoint_mgr.get_checkpoint = AsyncMock(side_effect=lambda cid: (
        Mock(checkpoint_id='ckpt-origin', instructions_path='/tmp/orig/instr.json')
        if cid == 'ckpt-origin'
        else Mock(checkpoint_id='ckpt-current', instructions_path='/tmp/curr/instr.json')
    ))
    
    detector = ValueDriftDetector(
        db=db,
        checkpoint_manager=checkpoint_mgr,
        timeline=timeline,
        origin_checkpoint_id='ckpt-origin',
    )
    
    # Check drift
    with patch('value_drift_detector.IdentityDiffEngine') as mock_engine_class:
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        diff = Mock(
            semantic_distance=150,
            instruction_delta=Mock(semantic_similarity=0.65),
            calibration_delta=Mock(temperature_shift=0.08),
            classifier_drift=0.06,
            skill_delta=Mock(skills_added=[], skills_removed=[], skills_modified=[]),
        )
        mock_engine.compute_diff = AsyncMock(return_value=diff)
        
        alert = await detector.check_drift('ckpt-current')
        
        # Should trigger warning-level alert
        assert alert is not None
        assert alert.alert_level == 'WARN'
        
        # Store alert
        await detector.store_alert(alert)
        assert db.execute.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
