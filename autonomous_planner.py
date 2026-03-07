"""
Autonomous Improvement Planner - Dimension 2

Continuously evaluates system health, identifies improvement opportunities,
and autonomously executes improvements. Shifts from reactive to proactive
self-maintenance. Foundation for future RL-based planning.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import logging

logger = logging.getLogger(__name__)


class SystemHealthDimension(str, Enum):
    """Five dimensions of system health that planner monitors."""
    CALIBRATION = "calibration"
    DATASET_COVERAGE = "coverage"
    SKILL_UTILIZATION = "skills"
    INSTRUCTION_DEBT = "debt"
    PREDICTION_STALENESS = "staleness"


class HealthTrend(str, Enum):
    """Direction of health metric over time."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


class ImprovementSubprocess(str, Enum):
    """Available improvement operations."""
    RECALIBRATE_CONFIDENCE = "recalibrate"
    PROBE_ADVERSARIAL = "adversarial"
    CRYSTALLIZE_SKILLS = "crystallize"
    RETRAIN_PREDICTOR = "predictor"
    DISTILL_INSTRUCTIONS = "distill"
    REOPTIMIZE_PARETO = "pareto"


@dataclass
class HealthMetric:
    """Represents health of one system dimension."""
    dimension: SystemHealthDimension
    current_score: float  # 0.0 (worst) to 1.0 (best)
    trend: HealthTrend
    days_since_check: int
    days_since_improvement: int
    threshold: float = 0.5  # Health falls below this, trigger improvement
    urgency_score: float = 0.0  # 0.0-1.0, higher = more urgent


@dataclass
class ImprovementPriority:
    """Single improvement candidate."""
    improvement_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dimension: SystemHealthDimension = SystemHealthDimension.CALIBRATION
    urgency_score: float = 0.0
    estimated_effort_hours: float = 2.0
    expected_impact: str = "MEDIUM"
    rationale: str = ""
    subprocess: ImprovementSubprocess = ImprovementSubprocess.RECALIBRATE_CONFIDENCE


@dataclass
class ImprovementPlan:
    """Complete improvement plan for one cycle."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=datetime.now)
    system_health_snapshot: Dict[str, HealthMetric] = field(default_factory=dict)
    prioritized_improvements: List[ImprovementPriority] = field(default_factory=list)
    top_priority: Optional[ImprovementPriority] = None
    estimated_total_hours: float = 0.0


@dataclass
class ExecutionResult:
    """Result of running one improvement."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str = ""
    improvement_id: str = ""
    subprocess: ImprovementSubprocess = ImprovementSubprocess.RECALIBRATE_CONFIDENCE
    status: str = "completed"  # completed, failed, skipped
    duration_minutes: float = 0.0
    metric_before: float = 0.0
    metric_after: float = 0.0
    improvement_delta: float = 0.0
    side_effects: List[str] = field(default_factory=list)
    recommendation: str = ""
    executed_at: datetime = field(default_factory=datetime.now)


class SystemHealthScorer:
    """Evaluates system health across all 5 dimensions."""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.thresholds = {
            SystemHealthDimension.CALIBRATION: 0.05,  # ECE target
            SystemHealthDimension.DATASET_COVERAGE: 0.05,  # Min category %
            SystemHealthDimension.SKILL_UTILIZATION: 0.30,  # Min usage %
            SystemHealthDimension.INSTRUCTION_DEBT: 30,  # Max days
            SystemHealthDimension.PREDICTION_STALENESS: 7,  # Max days
        }
    
    async def evaluate_all_dimensions(self) -> Dict[str, HealthMetric]:
        """Evaluate all 5 dimensions, return health metrics."""
        metrics = {}
        
        # Dimension 1: Calibration Error
        metrics[SystemHealthDimension.CALIBRATION.value] = await self._evaluate_calibration()
        
        # Dimension 2: Dataset Coverage
        metrics[SystemHealthDimension.DATASET_COVERAGE.value] = await self._evaluate_coverage()
        
        # Dimension 3: Skill Utilization
        metrics[SystemHealthDimension.SKILL_UTILIZATION.value] = await self._evaluate_skills()
        
        # Dimension 4: Instruction Debt
        metrics[SystemHealthDimension.INSTRUCTION_DEBT.value] = await self._evaluate_debt()
        
        # Dimension 5: Prediction Staleness
        metrics[SystemHealthDimension.PREDICTION_STALENESS.value] = await self._evaluate_staleness()
        
        # Compute urgency scores
        for metric in metrics.values():
            metric.urgency_score = self._compute_urgency_score(metric)
        
        return metrics
    
    async def _evaluate_calibration(self) -> HealthMetric:
        """Check calibration ECE from Direction 1."""
        try:
            result = await self.db.fetch(
                "SELECT ece FROM calibration_curves ORDER BY computed_at DESC LIMIT 1"
            )
            ece = result[0]['ece'] if result else 0.1
            current_score = max(0, 1.0 - (ece / 0.05))  # 1.0 at ECE=0, 0.0 at ECE=0.05+
        except Exception as e:
            logger.warning(f"Failed to evaluate calibration: {e}")
            ece = 0.5
            current_score = 0.0
        
        days_since = await self._days_since_last_update("calibration_curves")
        
        return HealthMetric(
            dimension=SystemHealthDimension.CALIBRATION,
            current_score=current_score,
            trend=self._detect_trend("calibration"),
            days_since_check=days_since,
            days_since_improvement=days_since,
            threshold=0.95
        )
    
    async def _evaluate_coverage(self) -> HealthMetric:
        """Check SFT dataset coverage from Direction 7."""
        try:
            result = await self.db.fetch("""
                SELECT scenario_category, COUNT(*) as count
                FROM jarvis_sft_dataset
                GROUP BY scenario_category
            """)
            
            if not result:
                return HealthMetric(
                    dimension=SystemHealthDimension.DATASET_COVERAGE,
                    current_score=0.0,
                    trend=HealthTrend.DEGRADING,
                    days_since_check=999,
                    days_since_improvement=999
                )
            
            total = sum(r['count'] for r in result)
            percentages = [r['count'] / total for r in result]
            min_percentage = min(percentages) if percentages else 0.0
            
            # Score: 1.0 if all categories >= 5%, 0.0 if any is 0%
            coverage_score = min(1.0, min_percentage / 0.05)
        except Exception as e:
            logger.warning(f"Failed to evaluate coverage: {e}")
            coverage_score = 0.5
        
        days_since = await self._days_since_last_update("jarvis_sft_dataset")
        
        return HealthMetric(
            dimension=SystemHealthDimension.DATASET_COVERAGE,
            current_score=coverage_score,
            trend=self._detect_trend("coverage"),
            days_since_check=days_since,
            days_since_improvement=days_since
        )
    
    async def _evaluate_skills(self) -> HealthMetric:
        """Check skill utilization from Direction 3."""
        try:
            skill_result = await self.db.fetch("SELECT COUNT(*) as count FROM skills")
            total_skills = skill_result[0]['count'] if skill_result else 0
            
            if total_skills == 0:
                utilization_score = 1.0  # No skills = no problem
            else:
                triggered = await self.db.fetch("""
                    SELECT COUNT(DISTINCT skill_id) as count
                    FROM skill_executions
                    WHERE executed_at > datetime('now', '-30 days')
                """)
                triggered_count = triggered[0]['count'] if triggered else 0
                utilization_score = min(1.0, triggered_count / total_skills)
        except Exception as e:
            logger.warning(f"Failed to evaluate skills: {e}")
            utilization_score = 0.5
        
        days_since = await self._days_since_last_update("skills")
        
        return HealthMetric(
            dimension=SystemHealthDimension.SKILL_UTILIZATION,
            current_score=utilization_score,
            trend=self._detect_trend("skills"),
            days_since_check=days_since,
            days_since_improvement=days_since
        )
    
    async def _evaluate_debt(self) -> HealthMetric:
        """Check instruction debt from Direction 5."""
        try:
            result = await self.db.fetch("""
                SELECT MAX(executed_at) as last_distill
                FROM improvement_executions
                WHERE subprocess = 'distill'
            """)
            last_distill = result[0]['last_distill'] if result and result[0]['last_distill'] else None
            
            if last_distill:
                days_since_distill = (datetime.now() - datetime.fromisoformat(last_distill)).days
            else:
                days_since_distill = 999  # Never distilled = high debt
            
            # Score: 1.0 if < 7 days, 0.0 if > 60 days
            debt_score = max(0, 1.0 - (days_since_distill / 60))
        except Exception as e:
            logger.warning(f"Failed to evaluate debt: {e}")
            debt_score = 0.5
            days_since_distill = 999
        
        return HealthMetric(
            dimension=SystemHealthDimension.INSTRUCTION_DEBT,
            current_score=debt_score,
            trend=self._detect_trend("debt"),
            days_since_check=0,
            days_since_improvement=days_since_distill
        )
    
    async def _evaluate_staleness(self) -> HealthMetric:
        """Check FailurePredictor staleness from Direction 4."""
        try:
            result = await self.db.fetch("""
                SELECT MAX(trained_at) as last_train
                FROM failure_predictor_models
            """)
            last_train = result[0]['last_train'] if result and result[0]['last_train'] else None
            
            if last_train:
                days_since_train = (datetime.now() - datetime.fromisoformat(last_train)).days
            else:
                days_since_train = 999
            
            # Score: 1.0 if < 1 day, 0.0 if > 14 days
            staleness_score = max(0, 1.0 - (days_since_train / 14))
        except Exception as e:
            logger.warning(f"Failed to evaluate staleness: {e}")
            staleness_score = 0.5
            days_since_train = 999
        
        return HealthMetric(
            dimension=SystemHealthDimension.PREDICTION_STALENESS,
            current_score=staleness_score,
            trend=self._detect_trend("staleness"),
            days_since_check=0,
            days_since_improvement=days_since_train
        )
    
    async def _days_since_last_update(self, table: str) -> int:
        """Days since table was last updated."""
        try:
            result = await self.db.fetch(f"""
                SELECT MAX(datetime('now') - MAX(created_at)) as days
                FROM {table}
            """)
            days = result[0]['days'] if result and result[0]['days'] else 999
            return int(days) if days else 999
        except:
            return 999
    
    def _detect_trend(self, dimension: str) -> HealthTrend:
        """Simple trend detection: improve, stable, degrade."""
        # In production, would compare recent metrics to older ones
        return HealthTrend.STABLE
    
    def _compute_urgency_score(self, metric: HealthMetric) -> float:
        """Weighted urgency score: current health + trend + recency."""
        weights = {
            'current': 0.40,
            'trend': 0.30,
            'recency': 0.30
        }
        
        # Current score: how bad is it now?
        current_component = (1.0 - metric.current_score) * weights['current']
        
        # Trend: is it getting worse?
        trend_penalty = {
            HealthTrend.IMPROVING: 0.0,
            HealthTrend.STABLE: 0.5,
            HealthTrend.DEGRADING: 1.0
        }
        trend_component = trend_penalty.get(metric.trend, 0.5) * weights['trend']
        
        # Recency: how long since we fixed it?
        recency_component = min(1.0, metric.days_since_improvement / 90) * weights['recency']
        
        return current_component + trend_component + recency_component


class ImprovementPlanner:
    """Constructs prioritized list of improvements."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    async def construct_plan(self, health_metrics: Dict[str, HealthMetric]) -> ImprovementPlan:
        """Create prioritized improvement plan from health metrics."""
        plan = ImprovementPlan(
            system_health_snapshot=health_metrics
        )
        
        # Create improvement candidate for each dimension
        candidates = []
        
        for dimension, metric in health_metrics.items():
            if metric.current_score < 0.95:  # Only if room for improvement
                candidate = self._create_improvement_candidate(metric)
                candidates.append(candidate)
        
        # Sort by urgency score (highest first)
        candidates.sort(key=lambda x: x.urgency_score, reverse=True)
        plan.prioritized_improvements = candidates
        
        if candidates:
            plan.top_priority = candidates[0]
            plan.estimated_total_hours = sum(c.estimated_effort_hours for c in candidates[:3])
        
        return plan
    
    def _create_improvement_candidate(self, metric: HealthMetric) -> ImprovementPriority:
        """Create improvement candidate from health metric."""
        dimension_to_subprocess = {
            SystemHealthDimension.CALIBRATION: ImprovementSubprocess.RECALIBRATE_CONFIDENCE,
            SystemHealthDimension.DATASET_COVERAGE: ImprovementSubprocess.PROBE_ADVERSARIAL,
            SystemHealthDimension.SKILL_UTILIZATION: ImprovementSubprocess.CRYSTALLIZE_SKILLS,
            SystemHealthDimension.PREDICTION_STALENESS: ImprovementSubprocess.RETRAIN_PREDICTOR,
            SystemHealthDimension.INSTRUCTION_DEBT: ImprovementSubprocess.DISTILL_INSTRUCTIONS,
        }
        
        impact_map = {
            SystemHealthDimension.CALIBRATION: "HIGH",
            SystemHealthDimension.DATASET_COVERAGE: "MEDIUM",
            SystemHealthDimension.SKILL_UTILIZATION: "MEDIUM",
            SystemHealthDimension.PREDICTION_STALENESS: "HIGH",
            SystemHealthDimension.INSTRUCTION_DEBT: "MEDIUM",
        }
        
        effort_map = {
            SystemHealthDimension.CALIBRATION: 2.0,
            SystemHealthDimension.DATASET_COVERAGE: 3.0,
            SystemHealthDimension.SKILL_UTILIZATION: 4.0,
            SystemHealthDimension.PREDICTION_STALENESS: 1.5,
            SystemHealthDimension.INSTRUCTION_DEBT: 6.0,
        }
        
        return ImprovementPriority(
            dimension=metric.dimension,
            urgency_score=metric.urgency_score,
            estimated_effort_hours=effort_map.get(metric.dimension, 2.0),
            expected_impact=impact_map.get(metric.dimension, "MEDIUM"),
            rationale=f"Health score {metric.current_score:.2f} below optimal, trend: {metric.trend.value}",
            subprocess=dimension_to_subprocess.get(metric.dimension, ImprovementSubprocess.RECALIBRATE_CONFIDENCE)
        )


class ImprovementExecutor:
    """Executes chosen improvement subprocess."""
    
    def __init__(self, db_connection, improvement_registry: Dict[ImprovementSubprocess, callable]):
        self.db = db_connection
        self.registry = improvement_registry
    
    async def execute_improvement(self, priority: ImprovementPriority, plan_id: str) -> ExecutionResult:
        """Execute highest-priority improvement subprocess."""
        result = ExecutionResult(
            plan_id=plan_id,
            improvement_id=priority.improvement_id,
            subprocess=priority.subprocess
        )
        
        # Get metric before
        scorer = SystemHealthScorer(self.db)
        metrics_before = await scorer.evaluate_all_dimensions()
        metric_key = priority.dimension.value
        if metric_key in metrics_before:
            result.metric_before = metrics_before[metric_key].current_score
        
        # Execute subprocess
        try:
            if priority.subprocess in self.registry:
                handler = self.registry[priority.subprocess]
                result.status, result.duration_minutes = await handler()
            else:
                result.status = "skipped"
                result.recommendation = f"No handler for {priority.subprocess}"
                return result
        except Exception as e:
            result.status = "failed"
            result.recommendation = str(e)
            logger.error(f"Improvement execution failed: {e}")
            return result
        
        # Get metric after
        metrics_after = await scorer.evaluate_all_dimensions()
        if metric_key in metrics_after:
            result.metric_after = metrics_after[metric_key].current_score
        
        result.improvement_delta = result.metric_after - result.metric_before
        result.recommendation = f"Delta: {result.improvement_delta:+.2f}, Status: {result.status}"
        
        # Log execution
        await self._log_execution(result)
        
        return result
    
    async def _log_execution(self, result: ExecutionResult):
        """Log improvement execution to database."""
        try:
            await self.db.execute(f"""
                INSERT INTO improvement_executions 
                (execution_id, plan_id, improvement_id, subprocess, status, 
                 duration_minutes, metric_before, metric_after, improvement_delta, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.execution_id, result.plan_id, result.improvement_id,
                result.subprocess.value, result.status, result.duration_minutes,
                result.metric_before, result.metric_after, result.improvement_delta,
                result.recommendation
            ))
        except Exception as e:
            logger.warning(f"Failed to log execution: {e}")


class BackgroundPlanner:
    """Main loop: continuously plan and execute improvements."""
    
    def __init__(self, db_connection, improvement_registry: Dict[ImprovementSubprocess, callable]):
        self.db = db_connection
        self.scorer = SystemHealthScorer(db_connection)
        self.planner = ImprovementPlanner(db_connection)
        self.executor = ImprovementExecutor(db_connection, improvement_registry)
        self.running = False
        self.planning_interval_hours = 1
    
    async def run(self):
        """Main background loop."""
        self.running = True
        logger.info("Starting Autonomous Improvement Planner")
        
        while self.running:
            try:
                await self.run_planning_cycle()
                await asyncio.sleep(self.planning_interval_hours * 3600)
            except Exception as e:
                logger.error(f"Planning cycle failed: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute on error
    
    async def run_planning_cycle(self) -> Tuple[ImprovementPlan, Optional[ExecutionResult]]:
        """Run one complete plan-and-execute cycle."""
        logger.info("Starting planning cycle")
        
        # Evaluate health
        health_metrics = await self.scorer.evaluate_all_dimensions()
        
        # Construct plan
        plan = await self.planner.construct_plan(health_metrics)
        
        # Execute top improvement
        exec_result = None
        if plan.top_priority:
            logger.info(
                f"Executing improvement: {plan.top_priority.dimension.value} "
                f"(urgency: {plan.top_priority.urgency_score:.2f})"
            )
            exec_result = await self.executor.execute_improvement(plan.top_priority, plan.plan_id)
            logger.info(f"Execution result: {exec_result.status}, delta: {exec_result.improvement_delta:+.2f}")
        else:
            logger.info("No improvements needed, system health is optimal")
        
        return plan, exec_result
    
    async def stop(self):
        """Stop the background planner."""
        self.running = False
        logger.info("Stopped Autonomous Improvement Planner")


# Example usage and registry setup
async def example_handlers():
    """Example improvement subprocess handlers."""
    
    async def recalibrate_confidence():
        """Direction 1: Recalibrate confidence scores."""
        logger.info("Running: Recalibrate Confidence")
        await asyncio.sleep(0.5)  # Simulated work
        return "completed", 2.0  # 2 minutes
    
    async def probe_adversarial():
        """Direction 2: Probe adversarial inputs."""
        logger.info("Running: Adversarial Probing")
        await asyncio.sleep(0.5)
        return "completed", 5.0
    
    async def crystallize_skills():
        """Direction 3: Crystallize skills."""
        logger.info("Running: Crystallize Skills")
        await asyncio.sleep(0.5)
        return "completed", 8.0
    
    async def retrain_predictor():
        """Direction 4: Retrain failure predictor."""
        logger.info("Running: Retrain Predictor")
        await asyncio.sleep(0.5)
        return "completed", 3.0
    
    async def distill_instructions():
        """Direction 5: Distill instructions."""
        logger.info("Running: Distill Instructions")
        await asyncio.sleep(0.5)
        return "completed", 12.0
    
    async def reoptimize_pareto():
        """Direction 6: Reoptimize Pareto frontier."""
        logger.info("Running: Reoptimize Pareto")
        await asyncio.sleep(0.5)
        return "completed", 1.5
    
    return {
        ImprovementSubprocess.RECALIBRATE_CONFIDENCE: recalibrate_confidence,
        ImprovementSubprocess.PROBE_ADVERSARIAL: probe_adversarial,
        ImprovementSubprocess.CRYSTALLIZE_SKILLS: crystallize_skills,
        ImprovementSubprocess.RETRAIN_PREDICTOR: retrain_predictor,
        ImprovementSubprocess.DISTILL_INSTRUCTIONS: distill_instructions,
        ImprovementSubprocess.REOPTIMIZE_PARETO: reoptimize_pareto,
    }
