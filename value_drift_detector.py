"""
ValueDriftDetector - Fifth Chapter: Identity (Phase 5)

Real-time monitoring for value drift and behavioral misalignment.
Detects when the system's behavior drifts from original baseline values.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal
import json

logger = logging.getLogger(__name__)


@dataclass
class DriftAlert:
    """Alert triggered by drift detection."""
    alert_id: str
    checkpoint_id: str
    alert_level: Literal["WARN", "ALERT"]
    metric_name: str
    metric_value: float
    threshold: float
    description: str
    created_at: datetime


class ValueDriftDetector:
    """
    Monitors system for behavioral drift from baseline values.
    
    Tracks:
    - Semantic distance from origin checkpoint
    - Instruction semantic similarity
    - Components changed in 24h
    - Drift trends
    
    Triggers alerts when drift indicates value misalignment.
    """
    
    def __init__(
        self,
        db,
        checkpoint_manager,
        timeline,
        origin_checkpoint_id: Optional[str] = None,
    ):
        """
        Initialize ValueDriftDetector.
        
        Args:
            db: Database connection
            checkpoint_manager: CheckpointManager instance
            timeline: BehavioralTimeline instance
            origin_checkpoint_id: Baseline checkpoint (first deployment)
        """
        self.db = db
        self.checkpoint_manager = checkpoint_manager
        self.timeline = timeline
        self.origin_checkpoint_id = origin_checkpoint_id
        
        # Thresholds for alerting
        self.thresholds = {
            'semantic_distance_warn': 100,           # 20% behavior change
            'semantic_distance_alert': 270,          # 50% behavior change
            'instruction_similarity_warn': 0.7,      # 30% instruction changes
            'sustained_drift_alert': 300,            # Cumulative distance over time
        }
    
    async def set_origin_checkpoint(self, checkpoint_id: str) -> None:
        """Set the baseline checkpoint for drift comparison."""
        checkpoint = await self.checkpoint_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        self.origin_checkpoint_id = checkpoint_id
        logger.info(f"Set origin checkpoint to {checkpoint_id}")
    
    async def check_drift(self, checkpoint_id: str) -> Optional[DriftAlert]:
        """
        Check if a checkpoint shows concerning drift.
        
        Returns alert if drift detected, None otherwise.
        """
        if not self.origin_checkpoint_id:
            logger.warning("Origin checkpoint not set, cannot check drift")
            return None
        
        checkpoint = await self.checkpoint_manager.get_checkpoint(checkpoint_id)
        origin = await self.checkpoint_manager.get_checkpoint(self.origin_checkpoint_id)
        
        if not checkpoint or not origin:
            raise ValueError("Checkpoint not found")
        
        # Compute semantic distance from origin
        try:
            from identity_diff_engine import IdentityDiffEngine
            engine = IdentityDiffEngine()
            
            diff = await engine.compute_diff(
                Path(origin.instructions_path).parent,
                Path(checkpoint.instructions_path).parent,
                self.origin_checkpoint_id,
                checkpoint_id,
            )
            
            semantic_distance = diff.semantic_distance
            instruction_similarity = diff.instruction_delta.semantic_similarity
            
        except Exception as e:
            logger.error(f"Failed to compute diff: {e}")
            return None
        
        # Check thresholds
        alerts = []
        
        # ALERT on large semantic distance
        if semantic_distance > self.thresholds['semantic_distance_alert']:
            alerts.append(DriftAlert(
                alert_id=f"drift-{checkpoint_id}-semantic",
                checkpoint_id=checkpoint_id,
                alert_level="ALERT",
                metric_name="semantic_distance_from_origin",
                metric_value=float(semantic_distance),
                threshold=float(self.thresholds['semantic_distance_alert']),
                description=f"System behavior has drifted significantly from baseline ({semantic_distance}/540 predictions differ)",
                created_at=datetime.now(),
            ))
        
        # WARN on moderate semantic distance
        elif semantic_distance > self.thresholds['semantic_distance_warn']:
            alerts.append(DriftAlert(
                alert_id=f"drift-{checkpoint_id}-semantic",
                checkpoint_id=checkpoint_id,
                alert_level="WARN",
                metric_name="semantic_distance_from_origin",
                metric_value=float(semantic_distance),
                threshold=float(self.thresholds['semantic_distance_warn']),
                description=f"Noticeable behavior change from baseline ({semantic_distance}/540 predictions differ)",
                created_at=datetime.now(),
            ))
        
        # WARN on significant instruction changes
        if instruction_similarity < self.thresholds['instruction_similarity_warn']:
            alerts.append(DriftAlert(
                alert_id=f"drift-{checkpoint_id}-instructions",
                checkpoint_id=checkpoint_id,
                alert_level="WARN",
                metric_name="instruction_semantic_similarity",
                metric_value=instruction_similarity,
                threshold=self.thresholds['instruction_similarity_warn'],
                description=f"Instructions have changed significantly from baseline (similarity: {instruction_similarity:.2f})",
                created_at=datetime.now(),
            ))
        
        # Return most severe alert
        if alerts:
            alerts.sort(key=lambda a: (a.alert_level == "WARN", a.created_at))
            return alerts[0]
        
        return None
    
    async def detect_sustained_drift(
        self,
        days: int = 7,
        cumulative_threshold: int = 300,
    ) -> Optional[DriftAlert]:
        """
        Detect sustained drift over a period.
        
        A drift period is when cumulative semantic distance keeps increasing,
        indicating ongoing behavioral change rather than one-time adjustment.
        """
        segments = await self.timeline.get_timeline_segments(days=days)
        
        cumulative_distance = 0
        increasing_periods = 0
        
        for i, seg in enumerate(segments):
            cumulative_distance += seg.semantic_distance
            
            # Check if increasing
            if i == 0 or seg.semantic_distance > segments[i-1].semantic_distance:
                increasing_periods += 1
        
        # Alert if sustained increase over threshold
        if cumulative_distance > cumulative_threshold and increasing_periods > len(segments) * 0.7:
            return DriftAlert(
                alert_id=f"drift-sustained-{segments[-1].checkpoint_b_id}",
                checkpoint_id=segments[-1].checkpoint_b_id,
                alert_level="ALERT",
                metric_name="sustained_drift",
                metric_value=float(cumulative_distance),
                threshold=float(cumulative_threshold),
                description=f"Sustained drift detected over {days} days (cumulative distance: {cumulative_distance}). System behavior continuously changing.",
                created_at=datetime.now(),
            )
        
        return None
    
    async def get_drift_metrics(
        self,
        checkpoint_id: str,
    ) -> Dict:
        """
        Get complete drift metrics for a checkpoint.
        
        Returns all monitored metrics and their values relative to baseline.
        """
        if not self.origin_checkpoint_id:
            raise ValueError("Origin checkpoint not set")
        
        checkpoint = await self.checkpoint_manager.get_checkpoint(checkpoint_id)
        origin = await self.checkpoint_manager.get_checkpoint(self.origin_checkpoint_id)
        
        if not checkpoint or not origin:
            raise ValueError("Checkpoint not found")
        
        try:
            from identity_diff_engine import IdentityDiffEngine
            from pathlib import Path
            engine = IdentityDiffEngine()
            
            diff = await engine.compute_diff(
                Path(origin.instructions_path).parent,
                Path(checkpoint.instructions_path).parent,
                self.origin_checkpoint_id,
                checkpoint_id,
            )
            
            metrics = {
                'semantic_distance_from_origin': diff.semantic_distance,
                'semantic_distance_from_origin_percentage': (diff.semantic_distance / 540) * 100,
                'instruction_semantic_similarity': diff.instruction_delta.semantic_similarity,
                'calibration_temperature_shift': diff.calibration_delta.temperature_shift,
                'classifier_drift': diff.classifier_drift,
                'skills_added': len(diff.skill_delta.skills_added),
                'skills_removed': len(diff.skill_delta.skills_removed),
                'skills_modified': len(diff.skill_delta.skills_modified),
                'is_drifting': diff.semantic_distance > self.thresholds['semantic_distance_warn'],
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to compute drift metrics: {e}")
            return {}
    
    async def get_alert_history(
        self,
        days: int = 30,
        alert_level: Optional[str] = None,
    ) -> List[DriftAlert]:
        """
        Get history of drift alerts.
        
        Returns recent alerts filtered by level if specified.
        """
        query = """
            SELECT * FROM value_drift_events
            WHERE created_at >= datetime('now', '-' || ? || ' days')
        """
        
        params = [days]
        
        if alert_level:
            query += " AND alert_level = ?"
            params.append(alert_level)
        
        query += " ORDER BY created_at DESC"
        
        results = await self.db.fetch(query, params)
        
        alerts = []
        for row in results:
            alert = DriftAlert(
                alert_id=row['id'],
                checkpoint_id=row['checkpoint_id'],
                alert_level=row['alert_level'],
                metric_name=row['metric_name'],
                metric_value=row['metric_value'],
                threshold=row['threshold'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']),
            )
            alerts.append(alert)
        
        return alerts
    
    async def store_alert(self, alert: DriftAlert) -> None:
        """Store alert in database."""
        query = """
            INSERT INTO value_drift_events (
                id, checkpoint_id, alert_level, metric_name,
                metric_value, threshold, description, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await self.db.execute(
            query,
            (
                alert.alert_id,
                alert.checkpoint_id,
                alert.alert_level,
                alert.metric_name,
                alert.metric_value,
                alert.threshold,
                alert.description,
                alert.created_at.isoformat(),
            )
        )
        
        logger.info(f"Stored drift alert: {alert.alert_id} ({alert.alert_level})")
    
    async def continuous_monitoring(
        self,
        check_interval_seconds: int = 3600,  # 1 hour
    ) -> None:
        """
        Continuous monitoring loop (run in background).
        
        Periodically checks latest checkpoint for drift and stores alerts.
        """
        import asyncio
        
        while True:
            try:
                # Get latest checkpoint
                checkpoints = await self.checkpoint_manager.list_checkpoints(limit=1)
                if not checkpoints:
                    await asyncio.sleep(check_interval_seconds)
                    continue
                
                latest = checkpoints[0]
                
                # Check for drift
                alert = await self.check_drift(latest.checkpoint_id)
                if alert:
                    await self.store_alert(alert)
                    logger.warning(f"Drift detected: {alert.description}")
                
                # Check for sustained drift
                sustained_alert = await self.detect_sustained_drift()
                if sustained_alert:
                    await self.store_alert(sustained_alert)
                    logger.error(f"ALERT: {sustained_alert.description}")
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
            
            await asyncio.sleep(check_interval_seconds)


# REST API endpoints
async def drift_endpoints(app, detector: ValueDriftDetector):
    """Register API endpoints for drift monitoring."""
    
    @app.get("/api/drift/metrics/{checkpoint_id}")
    async def get_metrics(checkpoint_id: str):
        """Get drift metrics for a checkpoint."""
        metrics = await detector.get_drift_metrics(checkpoint_id)
        return metrics
    
    @app.get("/api/drift/check/{checkpoint_id}")
    async def check_drift(checkpoint_id: str):
        """Check if checkpoint shows concerning drift."""
        alert = await detector.check_drift(checkpoint_id)
        return {
            'has_alert': alert is not None,
            'alert': alert.to_dict() if alert else None,
        }
    
    @app.get("/api/drift/history")
    async def get_history(days: int = 30, level: Optional[str] = None):
        """Get alert history."""
        alerts = await detector.get_alert_history(days=days, alert_level=level)
        return {
            'alerts': [
                {
                    'id': a.alert_id,
                    'level': a.alert_level,
                    'metric': a.metric_name,
                    'value': a.metric_value,
                    'threshold': a.threshold,
                    'description': a.description,
                    'timestamp': a.created_at.isoformat(),
                }
                for a in alerts
            ]
        }
    
    @app.get("/api/drift/sustained")
    async def check_sustained(days: int = 7):
        """Check for sustained drift."""
        alert = await detector.detect_sustained_drift(days=days)
        return {
            'detected': alert is not None,
            'alert': alert.to_dict() if alert else None,
        }
