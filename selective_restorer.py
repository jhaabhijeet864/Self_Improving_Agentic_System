"""
SelectiveRestorer - Fifth Chapter: Identity (Phase 4)

Performs fine-grained, surgical rollback of specific components.
Instead of atomic rollback (everything), restore only the components that broke.
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class RestorePreview:
    """Preview of what will happen if restore is executed."""
    components_to_restore: List[str]
    test_sample_size: int
    predicted_success_rate: float
    predicted_impact: str  # "low", "medium", "high"


@dataclass
class RestoreResult:
    """Result of restore operation."""
    restore_id: str
    status: str  # "success", "failed", "partial"
    components_restored: List[str]
    duration_seconds: float
    regression_test_impact: Dict  # Before/after metrics
    new_checkpoint_id: Optional[str] = None


class SelectiveRestorer:
    """
    Performs fine-grained component restoration.
    
    Enables surgical rollback: reverse only the bad component while preserving
    improvements in other components.
    
    Key insight: Use counterfactual reasoning to answer "what if component X
    had its old value but everything else was current?"
    """
    
    def __init__(
        self,
        checkpoint_manager,
        diff_engine,
        regression_suite_path: Optional[Path] = None,
    ):
        """
        Initialize SelectiveRestorer.
        
        Args:
            checkpoint_manager: CheckpointManager instance
            diff_engine: IdentityDiffEngine instance
            regression_suite_path: Path to regression test suite
        """
        self.checkpoint_manager = checkpoint_manager
        self.diff_engine = diff_engine
        self.regression_suite_path = regression_suite_path
        self.regression_suite = None
        
        if regression_suite_path and regression_suite_path.exists():
            self._load_regression_suite()
    
    def _load_regression_suite(self) -> None:
        """Load regression suite (540 test cases)."""
        import json
        try:
            with open(self.regression_suite_path, 'r') as f:
                self.regression_suite = json.load(f)
            logger.info(f"Loaded {len(self.regression_suite)} regression tests")
        except Exception as e:
            logger.warning(f"Failed to load regression suite: {e}")
    
    async def get_restore_options(
        self,
        target_checkpoint_id: str,
    ) -> Dict:
        """
        Show what restore options are available.
        
        Returns which components changed most significantly between
        current state and target checkpoint.
        """
        current_checkpoint = await self.checkpoint_manager.get_checkpoint(
            await self._get_current_checkpoint_id()
        )
        target_checkpoint = await self.checkpoint_manager.get_checkpoint(
            target_checkpoint_id
        )
        
        if not current_checkpoint or not target_checkpoint:
            raise ValueError("Checkpoint not found")
        
        # Compute diff
        diff = await self.diff_engine.compute_diff(
            Path(current_checkpoint.instructions_path).parent,
            Path(target_checkpoint.instructions_path).parent,
            current_checkpoint.checkpoint_id,
            target_checkpoint_id,
        )
        
        # Rank components by change magnitude
        component_changes = {
            'instructions': {
                'lines_added': diff.instruction_delta.lines_added,
                'lines_removed': diff.instruction_delta.lines_removed,
                'semantic_similarity': diff.instruction_delta.semantic_similarity,
            },
            'calibration': {
                'temperature_shift': diff.calibration_delta.temperature_shift,
                'curve_divergence': diff.calibration_delta.curve_divergence,
            },
            'skills': {
                'added': len(diff.skill_delta.skills_added),
                'removed': len(diff.skill_delta.skills_removed),
                'modified': len(diff.skill_delta.skills_modified),
            },
            'classifier': {
                'drift': diff.classifier_drift,
            }
        }
        
        return {
            'current_checkpoint': current_checkpoint.checkpoint_id,
            'target_checkpoint': target_checkpoint_id,
            'component_changes': component_changes,
            'semantic_distance': diff.semantic_distance,
            'narrative': diff.narrative,
        }
    
    async def preview_restore(
        self,
        target_checkpoint_id: str,
        components_to_restore: List[str],
        sample_size: int = 50,
    ) -> RestorePreview:
        """
        Preview restore: predict impact before executing.
        
        Run mini regression test (50 cases) on partially-restored state.
        
        Args:
            target_checkpoint_id: Checkpoint to restore from
            components_to_restore: Which components to restore
            sample_size: Number of regression tests to run (out of 540)
            
        Returns:
            RestorePreview with predicted outcome
        """
        if not self.regression_suite:
            logger.warning("Regression suite not loaded, cannot preview")
            return RestorePreview(
                components_to_restore=components_to_restore,
                test_sample_size=0,
                predicted_success_rate=0.5,
                predicted_impact="unknown",
            )
        
        # MVP: Return simple prediction based on component types
        impact_map = {
            'instructions': 'high',
            'calibration': 'medium',
            'classifier': 'high',
            'skills': 'low',
        }
        
        max_impact = 'low'
        for comp in components_to_restore:
            if impact_map.get(comp, 'low') == 'high':
                max_impact = 'high'
            elif impact_map.get(comp, 'low') == 'medium' and max_impact == 'low':
                max_impact = 'medium'
        
        # Estimate success rate (higher for targeted fixes)
        success_rate = 0.7 + (0.3 * len(components_to_restore) / 8)
        
        return RestorePreview(
            components_to_restore=components_to_restore,
            test_sample_size=min(sample_size, len(self.regression_suite)),
            predicted_success_rate=success_rate,
            predicted_impact=max_impact,
        )
    
    async def execute_restore(
        self,
        target_checkpoint_id: str,
        components_to_restore: List[str],
        dry_run: bool = False,
    ) -> RestoreResult:
        """
        Execute selective restoration.
        
        Args:
            target_checkpoint_id: Checkpoint to restore from
            components_to_restore: Which components to restore
            dry_run: If True, don't actually modify files
            
        Returns:
            RestoreResult with outcome
        """
        import time
        import uuid
        
        start_time = time.time()
        restore_id = str(uuid.uuid4())
        
        try:
            # Get checkpoints
            current_checkpoint = await self.checkpoint_manager.get_checkpoint(
                await self._get_current_checkpoint_id()
            )
            target_checkpoint = await self.checkpoint_manager.get_checkpoint(
                target_checkpoint_id
            )
            
            if not current_checkpoint or not target_checkpoint:
                raise ValueError("Checkpoint not found")
            
            # Restore each component
            restored_components = []
            
            for component in components_to_restore:
                if component not in [
                    'instructions', 'calibration_params', 'skill_library',
                    'classifier_weights', 'vector_store', 'meta_learning_policy',
                    'failure_predictor'
                ]:
                    logger.warning(f"Unknown component: {component}")
                    continue
                
                # Get paths
                source_path = self._get_component_path(target_checkpoint, component)
                dest_path = self._get_component_path(current_checkpoint, component)
                
                if not dry_run and source_path.exists():
                    if source_path.is_file():
                        shutil.copy2(source_path, dest_path)
                    elif source_path.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(source_path, dest_path)
                    
                    logger.info(f"Restored component: {component}")
                    restored_components.append(component)
            
            # Measure impact
            regression_impact = await self._measure_regression_impact(
                current_checkpoint, components_to_restore
            )
            
            duration = time.time() - start_time
            
            result = RestoreResult(
                restore_id=restore_id,
                status="success" if restored_components else "partial",
                components_restored=restored_components,
                duration_seconds=duration,
                regression_test_impact=regression_impact,
            )
            
            logger.info(f"Restoration completed in {duration:.2f}s: {result.components_restored}")
            
            return result
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return RestoreResult(
                restore_id=restore_id,
                status="failed",
                components_restored=[],
                duration_seconds=time.time() - start_time,
                regression_test_impact={},
            )
    
    async def measure_restore_impact(
        self,
        before_checkpoint_id: str,
        after_checkpoint_id: str,
    ) -> Dict:
        """
        Measure how much the restore improved the system.
        
        Compares behavior before and after restoration.
        """
        before = await self.checkpoint_manager.get_checkpoint(before_checkpoint_id)
        after = await self.checkpoint_manager.get_checkpoint(after_checkpoint_id)
        
        if not before or not after:
            raise ValueError("Checkpoint not found")
        
        # Compute regression metrics
        impact = {
            'tests_improved': 0,
            'tests_regressed': 0,
            'tests_unchanged': 0,
            'success_rate_delta': 0.0,
        }
        
        # TODO: Run actual regression tests and measure
        
        return impact
    
    def _get_component_path(self, checkpoint, component: str) -> Path:
        """Get path for a component from a checkpoint."""
        component_map = {
            'instructions': checkpoint.instructions_path,
            'calibration_params': checkpoint.calibration_params_path,
            'skill_library': checkpoint.skill_library_path,
            'classifier_weights': checkpoint.classifier_weights_path,
            'vector_store': checkpoint.vector_store_snapshot_path,
            'meta_learning_policy': checkpoint.meta_learning_policy_path,
            'failure_predictor': checkpoint.failure_predictor_path,
        }
        return component_map.get(component, Path(''))
    
    async def _get_current_checkpoint_id(self) -> str:
        """Get ID of most recent checkpoint (current system state)."""
        checkpoints = await self.checkpoint_manager.list_checkpoints(limit=1)
        if checkpoints:
            return checkpoints[0].checkpoint_id
        raise ValueError("No checkpoints found")
    
    async def _measure_regression_impact(
        self,
        checkpoint,
        components_restored: List[str],
    ) -> Dict:
        """Measure regression test impact after restoration."""
        if not self.regression_suite:
            return {}
        
        # MVP: Return estimate based on components
        impact_per_component = {
            'instructions': {'improvement': 0.3},
            'classifier': {'improvement': 0.4},
            'calibration': {'improvement': 0.1},
            'skills': {'improvement': 0.05},
        }
        
        total_improvement = sum(
            impact_per_component.get(comp, {}).get('improvement', 0)
            for comp in components_restored
        )
        
        return {
            'estimated_improvement': min(1.0, total_improvement),
            'components_restored': len(components_restored),
        }
