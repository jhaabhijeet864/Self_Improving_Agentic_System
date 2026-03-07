"""
BehavioralTimeline - Fifth Chapter: Identity (Phase 3)

Dashboard component for visualizing system evolution over time.
Provides querying and visualization of checkpoints and their diffs.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TimelineCheckpoint:
    """Checkpoint data for timeline visualization."""
    checkpoint_id: str
    created_at: datetime
    label: str
    trigger: str
    semantic_distance_from_prev: Optional[int]
    change_narrative: str
    health_snapshot: Dict


@dataclass
class TimelineSegment:
    """Connection between two consecutive checkpoints."""
    checkpoint_a_id: str
    checkpoint_b_id: str
    semantic_distance: int
    created_at: datetime


class BehavioralTimeline:
    """
    Dashboard component for visualizing system evolution.
    
    Provides:
    - Timeline view (sequential checkpoints)
    - Diff visualization (component-level changes)
    - Querying (by date, trigger, label)
    - Anomaly detection (semantic distance spikes)
    """
    
    def __init__(self, db, checkpoint_manager, diff_engine):
        """
        Initialize BehavioralTimeline.
        
        Args:
            db: Database connection
            checkpoint_manager: CheckpointManager instance
            diff_engine: IdentityDiffEngine instance
        """
        self.db = db
        self.checkpoint_manager = checkpoint_manager
        self.diff_engine = diff_engine
    
    async def get_timeline(
        self,
        days: int = 30,
        limit: int = 100,
    ) -> List[TimelineCheckpoint]:
        """
        Get timeline view of checkpoints over recent period.
        
        Returns list of checkpoints with semantic distance to previous.
        """
        checkpoints = await self.checkpoint_manager.get_checkpoint_history(days=days)
        
        timeline = []
        prev_checkpoint = None
        
        for checkpoint in checkpoints:
            semantic_distance = None
            
            # Compute semantic distance from previous
            if prev_checkpoint:
                try:
                    diff = await self.diff_engine.compute_diff(
                        Path(prev_checkpoint.instructions_path).parent,
                        Path(checkpoint.instructions_path).parent,
                        prev_checkpoint.checkpoint_id,
                        checkpoint.checkpoint_id,
                    )
                    semantic_distance = diff.semantic_distance
                    
                    # Store diff in database
                    await self._store_diff(diff)
                except Exception as e:
                    logger.error(f"Failed to compute diff: {e}")
            
            timeline.append(TimelineCheckpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                created_at=checkpoint.created_at,
                label=checkpoint.label,
                trigger=checkpoint.trigger.value,
                semantic_distance_from_prev=semantic_distance,
                change_narrative=checkpoint.change_narrative,
                health_snapshot={
                    'calibration_error': checkpoint.health_snapshot.calibration_error,
                    'dataset_coverage': checkpoint.health_snapshot.dataset_coverage,
                    'skill_utilization': checkpoint.health_snapshot.skill_utilization,
                    'instruction_debt_days': checkpoint.health_snapshot.instruction_debt_days,
                    'failure_prediction_staleness': checkpoint.health_snapshot.failure_prediction_staleness_days,
                },
            ))
            
            prev_checkpoint = checkpoint
        
        return timeline[:limit]
    
    async def get_timeline_segments(
        self,
        days: int = 30,
    ) -> List[TimelineSegment]:
        """
        Get segments (connections) between consecutive checkpoints.
        
        Used for drawing arrows in timeline visualization.
        """
        checkpoints = await self.checkpoint_manager.get_checkpoint_history(days=days)
        
        segments = []
        
        for i in range(len(checkpoints) - 1):
            checkpoint_a = checkpoints[i]
            checkpoint_b = checkpoints[i + 1]
            
            try:
                diff = await self.diff_engine.compute_diff(
                    Path(checkpoint_a.instructions_path).parent,
                    Path(checkpoint_b.instructions_path).parent,
                    checkpoint_a.checkpoint_id,
                    checkpoint_b.checkpoint_id,
                )
                
                segments.append(TimelineSegment(
                    checkpoint_a_id=checkpoint_a.checkpoint_id,
                    checkpoint_b_id=checkpoint_b.checkpoint_id,
                    semantic_distance=diff.semantic_distance,
                    created_at=checkpoint_b.created_at,
                ))
            except Exception as e:
                logger.warning(f"Failed to compute segment diff: {e}")
        
        return segments
    
    async def find_anomalies(
        self,
        days: int = 30,
        semantic_distance_threshold: int = 100,
    ) -> List[Tuple[str, str, int]]:
        """
        Find anomalous semantic distance spikes.
        
        Returns list of (checkpoint_a_id, checkpoint_b_id, semantic_distance)
        where semantic_distance exceeds threshold.
        """
        segments = await self.get_timeline_segments(days=days)
        
        anomalies = [
            (seg.checkpoint_a_id, seg.checkpoint_b_id, seg.semantic_distance)
            for seg in segments
            if seg.semantic_distance > semantic_distance_threshold
        ]
        
        return anomalies
    
    async def query_checkpoints(
        self,
        trigger: Optional[str] = None,
        label_contains: Optional[str] = None,
        days: int = 30,
        limit: int = 100,
    ) -> List[TimelineCheckpoint]:
        """
        Query checkpoints by various criteria.
        
        Args:
            trigger: Filter by trigger type (scheduled, pre_mutation, etc.)
            label_contains: Filter by label substring
            days: Search last N days
            limit: Max results
            
        Returns:
            List of matching TimelineCheckpoint objects
        """
        checkpoints = await self.checkpoint_manager.get_checkpoint_history(days=days)
        
        results = []
        for checkpoint in checkpoints:
            if trigger and checkpoint.trigger.value != trigger:
                continue
            if label_contains and label_contains not in checkpoint.label:
                continue
            
            results.append(TimelineCheckpoint(
                checkpoint_id=checkpoint.checkpoint_id,
                created_at=checkpoint.created_at,
                label=checkpoint.label,
                trigger=checkpoint.trigger.value,
                semantic_distance_from_prev=None,  # Computed on demand
                change_narrative=checkpoint.change_narrative,
                health_snapshot={
                    'calibration_error': checkpoint.health_snapshot.calibration_error,
                    'dataset_coverage': checkpoint.health_snapshot.dataset_coverage,
                    'skill_utilization': checkpoint.health_snapshot.skill_utilization,
                    'instruction_debt_days': checkpoint.health_snapshot.instruction_debt_days,
                    'failure_prediction_staleness': checkpoint.health_snapshot.failure_prediction_staleness_days,
                },
            ))
        
        return results[:limit]
    
    async def compare_checkpoints(
        self,
        checkpoint_a_id: str,
        checkpoint_b_id: str,
    ) -> Dict:
        """
        Compare two arbitrary checkpoints (not necessarily adjacent).
        
        Returns detailed diff with all component-level changes.
        """
        checkpoint_a = await self.checkpoint_manager.get_checkpoint(checkpoint_a_id)
        checkpoint_b = await self.checkpoint_manager.get_checkpoint(checkpoint_b_id)
        
        if not checkpoint_a or not checkpoint_b:
            raise ValueError(f"Checkpoint not found")
        
        diff = await self.diff_engine.compute_diff(
            Path(checkpoint_a.instructions_path).parent,
            Path(checkpoint_b.instructions_path).parent,
            checkpoint_a_id,
            checkpoint_b_id,
        )
        
        return {
            'checkpoint_a': {
                'id': checkpoint_a.checkpoint_id,
                'label': checkpoint_a.label,
                'created_at': checkpoint_a.created_at.isoformat(),
            },
            'checkpoint_b': {
                'id': checkpoint_b.checkpoint_id,
                'label': checkpoint_b.label,
                'created_at': checkpoint_b.created_at.isoformat(),
            },
            'diff': diff.to_dict(),
        }
    
    async def get_semantic_distance_trend(
        self,
        days: int = 30,
    ) -> List[Dict]:
        """
        Get semantic distance over time for visualization.
        
        Returns list of (timestamp, semantic_distance) pairs.
        """
        segments = await self.get_timeline_segments(days=days)
        
        trend = [
            {
                'timestamp': seg.created_at.isoformat(),
                'semantic_distance': seg.semantic_distance,
                'from_checkpoint': seg.checkpoint_a_id,
                'to_checkpoint': seg.checkpoint_b_id,
            }
            for seg in segments
        ]
        
        return trend
    
    async def identify_drift_periods(
        self,
        days: int = 30,
        window_size: int = 5,  # Number of checkpoints
        threshold: int = 150,  # Cumulative semantic distance
    ) -> List[Dict]:
        """
        Identify periods of sustained drift.
        
        A drift period is when consecutive checkpoints show sustained
        high semantic distance (indicating ongoing behavioral change).
        """
        segments = await self.get_timeline_segments(days=days)
        
        drift_periods = []
        current_drift = []
        cumulative_distance = 0
        
        for seg in segments:
            if seg.semantic_distance > 50:  # Entering drift
                if not current_drift:
                    current_drift = [seg]
                    cumulative_distance = seg.semantic_distance
                else:
                    current_drift.append(seg)
                    cumulative_distance += seg.semantic_distance
            else:  # Not drifting
                if current_drift and cumulative_distance > threshold:
                    drift_periods.append({
                        'start_checkpoint': current_drift[0].checkpoint_a_id,
                        'end_checkpoint': current_drift[-1].checkpoint_b_id,
                        'duration_checkpoints': len(current_drift),
                        'cumulative_distance': cumulative_distance,
                    })
                current_drift = []
                cumulative_distance = 0
        
        return drift_periods
    
    async def _store_diff(self, diff) -> None:
        """Store diff in database for caching."""
        import json
        query = """
            INSERT OR REPLACE INTO checkpoint_diffs (
                id, checkpoint_a_id, checkpoint_b_id, semantic_distance,
                instruction_delta_json, calibration_delta_json, skill_delta_json,
                classifier_drift, narrative, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        diff_id = f"diff-{diff.checkpoint_a_id}-{diff.checkpoint_b_id}"
        
        await self.db.execute(
            query,
            (
                diff_id,
                diff.checkpoint_a_id,
                diff.checkpoint_b_id,
                diff.semantic_distance,
                json.dumps(diff.instruction_delta.to_dict()),
                json.dumps(diff.calibration_delta.to_dict()),
                json.dumps(diff.skill_delta.to_dict()),
                diff.classifier_drift,
                diff.narrative,
                datetime.now().isoformat(),
            )
        )


# REST API endpoints (for integration with dashboard)
async def timeline_endpoints(app, timeline: BehavioralTimeline):
    """Register API endpoints for timeline."""
    
    @app.get("/api/timeline")
    async def get_timeline(days: int = 30, limit: int = 100):
        """Get timeline view."""
        checkpoints = await timeline.get_timeline(days=days, limit=limit)
        return {
            'checkpoints': [
                {
                    'id': c.checkpoint_id,
                    'label': c.label,
                    'timestamp': c.created_at.isoformat(),
                    'trigger': c.trigger,
                    'semantic_distance': c.semantic_distance_from_prev,
                    'narrative': c.change_narrative,
                    'health': c.health_snapshot,
                }
                for c in checkpoints
            ]
        }
    
    @app.get("/api/timeline/anomalies")
    async def get_anomalies(days: int = 30, threshold: int = 100):
        """Get semantic distance anomalies."""
        anomalies = await timeline.find_anomalies(days=days, semantic_distance_threshold=threshold)
        return {'anomalies': anomalies}
    
    @app.get("/api/timeline/trend")
    async def get_trend(days: int = 30):
        """Get semantic distance trend."""
        trend = await timeline.get_semantic_distance_trend(days=days)
        return {'trend': trend}
    
    @app.get("/api/timeline/drift")
    async def get_drift(days: int = 30):
        """Get drift periods."""
        periods = await timeline.identify_drift_periods(days=days)
        return {'drift_periods': periods}
    
    @app.get("/api/checkpoints/compare")
    async def compare(checkpoint_a_id: str, checkpoint_b_id: str):
        """Compare two checkpoints."""
        result = await timeline.compare_checkpoints(checkpoint_a_id, checkpoint_b_id)
        return result
