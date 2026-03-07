"""
Tests for Autonomous Improvement Planner (Dimension 2)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from autonomous_planner import (
    SystemHealthDimension,
    HealthTrend,
    HealthMetric,
    ImprovementSubprocess,
    SystemHealthScorer,
    ImprovementPlanner,
    ImprovementExecutor,
    BackgroundPlanner,
)


class MockDB:
    """Mock database for testing."""
    
    def __init__(self):
        self.data = {}
    
    async def fetch(self, query: str):
        """Mock fetch."""
        # Return based on query
        if "calibration_curves" in query:
            return [{'ece': 0.12}]  # High calibration error
        elif "scenario_category" in query:
            return [
                {'scenario_category': 'app_launch', 'count': 100},
                {'scenario_category': 'file_search', 'count': 20},
                {'scenario_category': 'shell_command', 'count': 300},
            ]
        elif "COUNT(*)" in query and "skills" in query:
            return [{'count': 10}]
        elif "skill_executions" in query:
            return [{'count': 3}]
        elif "last_distill" in query:
            # Last distilled 60 days ago
            last_date = (datetime.now() - timedelta(days=60)).isoformat()
            return [{'last_distill': last_date}]
        elif "last_train" in query:
            # Last trained 5 days ago
            last_date = (datetime.now() - timedelta(days=5)).isoformat()
            return [{'last_train': last_date}]
        return []
    
    async def execute(self, query: str, params=None):
        """Mock execute."""
        pass


@pytest.mark.asyncio
async def test_health_scorer_evaluates_calibration():
    """Test that scorer correctly evaluates calibration dimension."""
    db = MockDB()
    scorer = SystemHealthScorer(db)
    
    metrics = await scorer.evaluate_all_dimensions()
    
    # Should have all 5 dimensions
    assert len(metrics) == 5
    assert SystemHealthDimension.CALIBRATION.value in metrics
    
    # Calibration with ECE=0.12 should have low score (threshold is 0.05)
    cal_metric = metrics[SystemHealthDimension.CALIBRATION.value]
    assert cal_metric.current_score < 0.5  # Below 0.5 means degraded


@pytest.mark.asyncio
async def test_health_scorer_evaluates_coverage():
    """Test dataset coverage evaluation."""
    db = MockDB()
    scorer = SystemHealthScorer(db)
    
    metrics = await scorer.evaluate_all_dimensions()
    
    coverage_metric = metrics[SystemHealthDimension.DATASET_COVERAGE.value]
    # With categories having [100, 20, 300], min is 20/420 = 4.8% < 5%
    assert coverage_metric.current_score < 1.0


@pytest.mark.asyncio
async def test_planner_prioritizes_worst_dimension():
    """Core test: planner identifies and prioritizes worst dimension."""
    db = MockDB()
    scorer = SystemHealthScorer(db)
    planner = ImprovementPlanner(db)
    
    # Get health metrics
    health_metrics = await scorer.evaluate_all_dimensions()
    
    # Create plan
    plan = await planner.construct_plan(health_metrics)
    
    # Assert: plan has priorities
    assert plan.top_priority is not None
    assert len(plan.prioritized_improvements) > 0
    
    # Assert: top priority has reasonable urgency
    assert plan.top_priority.urgency_score > 0.0
    assert plan.top_priority.urgency_score <= 1.0
    
    # Assert: top priority is worse than others
    if len(plan.prioritized_improvements) > 1:
        assert (plan.top_priority.urgency_score >= 
                plan.prioritized_improvements[1].urgency_score)


@pytest.mark.asyncio
async def test_executor_executes_improvement():
    """Test that executor runs improvement subprocess."""
    db = MockDB()
    
    # Create mock handler registry
    handlers = {
        ImprovementSubprocess.RECALIBRATE_CONFIDENCE: AsyncMock(
            return_value=("completed", 2.0)
        ),
    }
    
    executor = ImprovementExecutor(db, handlers)
    
    # Create improvement
    priority = ImprovementPriority(
        dimension=SystemHealthDimension.CALIBRATION,
        subprocess=ImprovementSubprocess.RECALIBRATE_CONFIDENCE,
        urgency_score=0.8,
    )
    
    # Execute
    result = await executor.execute_improvement(priority, "plan-123")
    
    # Assert
    assert result.status == "completed"
    assert result.duration_minutes == 2.0
    handlers[ImprovementSubprocess.RECALIBRATE_CONFIDENCE].assert_called_once()


@pytest.mark.asyncio
async def test_full_planning_cycle():
    """Integration test: full cycle of evaluation, planning, execution."""
    db = MockDB()
    
    # Handler registry
    handlers = {
        ImprovementSubprocess.RECALIBRATE_CONFIDENCE: AsyncMock(
            return_value=("completed", 2.0)
        ),
        ImprovementSubprocess.PROBE_ADVERSARIAL: AsyncMock(
            return_value=("completed", 5.0)
        ),
        ImprovementSubprocess.CRYSTALLIZE_SKILLS: AsyncMock(
            return_value=("completed", 4.0)
        ),
        ImprovementSubprocess.RETRAIN_PREDICTOR: AsyncMock(
            return_value=("completed", 3.0)
        ),
        ImprovementSubprocess.DISTILL_INSTRUCTIONS: AsyncMock(
            return_value=("completed", 6.0)
        ),
        ImprovementSubprocess.REOPTIMIZE_PARETO: AsyncMock(
            return_value=("completed", 1.5)
        ),
    }
    
    planner = BackgroundPlanner(db, handlers)
    plan, exec_result = await planner.run_planning_cycle()
    
    # Assert plan was created
    assert plan is not None
    assert plan.top_priority is not None
    
    # Assert execution happened
    assert exec_result is not None
    assert exec_result.status in ["completed", "failed", "skipped"]


@pytest.mark.asyncio
async def test_urgency_score_calculation():
    """Test urgency score combines all factors."""
    scorer = SystemHealthScorer(MockDB())
    
    # Create metric with high urgency
    metric = HealthMetric(
        dimension=SystemHealthDimension.CALIBRATION,
        current_score=0.2,  # Bad (40% current component)
        trend=HealthTrend.DEGRADING,  # Worse (30% trend component)
        days_since_check=90,  # Not checked recently (27% recency component)
        days_since_improvement=90,  # Not improved recently
    )
    
    urgency = scorer._compute_urgency_score(metric)
    
    # Should be high due to all factors
    assert urgency > 0.7


@pytest.mark.asyncio
async def test_stable_system_no_urgent_improvements():
    """Test that healthy system has low urgency scores."""
    scorer = SystemHealthScorer(MockDB())
    
    # Create metric with good health
    metric = HealthMetric(
        dimension=SystemHealthDimension.CALIBRATION,
        current_score=0.98,  # Good
        trend=HealthTrend.IMPROVING,  # Better
        days_since_check=1,  # Recently checked
        days_since_improvement=3,  # Recently improved
    )
    
    urgency = scorer._compute_urgency_score(metric)
    
    # Should be low
    assert urgency < 0.2


def test_dimension_enum_completeness():
    """Verify all dimensions are defined."""
    assert SystemHealthDimension.CALIBRATION
    assert SystemHealthDimension.DATASET_COVERAGE
    assert SystemHealthDimension.SKILL_UTILIZATION
    assert SystemHealthDimension.INSTRUCTION_DEBT
    assert SystemHealthDimension.PREDICTION_STALENESS


def test_subprocess_enum_completeness():
    """Verify all subprocesses are defined."""
    assert ImprovementSubprocess.RECALIBRATE_CONFIDENCE
    assert ImprovementSubprocess.PROBE_ADVERSARIAL
    assert ImprovementSubprocess.CRYSTALLIZE_SKILLS
    assert ImprovementSubprocess.RETRAIN_PREDICTOR
    assert ImprovementSubprocess.DISTILL_INSTRUCTIONS
    assert ImprovementSubprocess.REOPTIMIZE_PARETO


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
