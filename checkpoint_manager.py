"""
CheckpointManager - Fifth Chapter: Identity (Phase 1)

Manages behavioral checkpoints that capture the complete emergent identity of the system
at a moment in time. Each checkpoint snapshots all 8 identity components and generates
an LLM-powered explanation of what changed.

Identity components:
1. instructions.md                - System behavioral policy
2. calibration_params             - Temperature scalar + calibration curve
3. SkillLibrary                    - Crystallized procedures
4. LocalClassifier weights         - Routing decision model
5. ChromaDB vector store           - Project context / semantic memory
6. meta_learning_policy            - Best prompt templates + yield rates
7. FailurePredictor                - Anomaly detection model
8. SFT dataset hash                - SHA-256 of training data
"""

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Literal
from uuid import UUID, uuid4
import hashlib

logger = logging.getLogger(__name__)


class CheckpointTrigger(str, Enum):
    """What caused this checkpoint to be created."""
    SCHEDULED = "scheduled"              # Regular interval checkpoint
    PRE_MUTATION = "pre_mutation"        # Before applying a mutation
    POST_DISTILLATION = "post_distillation"  # After knowledge consolidation
    MANUAL = "manual"                    # Explicitly requested by operator
    ANOMALY_DETECTED = "anomaly_detected"   # System detected unusual behavior


@dataclass
class SystemHealthSnapshot:
    """Health metrics at time of checkpoint."""
    calibration_error: float            # Expected Calibration Error (ECE)
    dataset_coverage: float             # Min category percentage
    skill_utilization: float            # % of skills triggered
    instruction_debt_days: int          # Days since last distillation
    failure_prediction_staleness_days: int  # Days since predictor retrained
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BehavioralCheckpoint:
    """Complete snapshot of system identity at a moment in time."""
    checkpoint_id: str                  # UUID string
    created_at: datetime
    label: str                          # Human-readable label
    change_narrative: str               # LLM-generated explanation of what changed
    
    # The 8 identity components (stored as file paths)
    instructions_path: Path
    calibration_params_path: Path
    skill_library_path: Path
    classifier_weights_path: Path
    vector_store_snapshot_path: Path
    meta_learning_policy_path: Path
    failure_predictor_path: Path
    sft_dataset_hash: str              # SHA-256, not full dataset
    
    # Provenance
    trigger: CheckpointTrigger
    health_snapshot: SystemHealthSnapshot
    parent_checkpoint_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Serialize checkpoint to dictionary."""
        data = asdict(self)
        data['checkpoint_id'] = str(self.checkpoint_id)
        data['created_at'] = self.created_at.isoformat()
        data['instructions_path'] = str(self.instructions_path)
        data['calibration_params_path'] = str(self.calibration_params_path)
        data['skill_library_path'] = str(self.skill_library_path)
        data['classifier_weights_path'] = str(self.classifier_weights_path)
        data['vector_store_snapshot_path'] = str(self.vector_store_snapshot_path)
        data['meta_learning_policy_path'] = str(self.meta_learning_policy_path)
        data['failure_predictor_path'] = str(self.failure_predictor_path)
        data['trigger'] = self.trigger.value
        data['health_snapshot']['timestamp'] = self.health_snapshot.timestamp.isoformat()
        return data


class CheckpointManager:
    """
    Creates and manages behavioral checkpoints.
    
    Responsibilities:
    - Serialize all 8 identity components
    - Generate change narratives via LLM
    - Store checkpoints in SQLite + artifact storage
    - Maintain linked list (history chain)
    - Query and retrieve checkpoints
    """
    
    def __init__(
        self,
        db,
        artifact_root: Path,
        cloud_llm_client=None,  # For generating narratives
    ):
        """
        Initialize CheckpointManager.
        
        Args:
            db: Database connection (async SQLite)
            artifact_root: Root directory for storing checkpoint artifacts
            cloud_llm_client: Client for cloud LLM (generates narratives)
        """
        self.db = db
        self.artifact_root = artifact_root
        self.cloud_llm = cloud_llm_client
        
        # Create artifact root if needed
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        
    async def create_checkpoint(
        self,
        trigger: CheckpointTrigger,
        label: Optional[str] = None,
        health_snapshot: Optional[SystemHealthSnapshot] = None,
        identity_components: Optional[Dict[str, Path]] = None,
        sft_dataset_hash: Optional[str] = None,
    ) -> BehavioralCheckpoint:
        """
        Create a new behavioral checkpoint.
        
        Args:
            trigger: What caused this checkpoint
            label: Human-readable label (auto-generated if not provided)
            health_snapshot: System health at checkpoint time
            identity_components: Dict with keys: instructions, calibration_params,
                                skill_library, classifier_weights, vector_store,
                                meta_learning_policy, failure_predictor
            sft_dataset_hash: SHA-256 of SFT dataset
            
        Returns:
            BehavioralCheckpoint with all metadata and artifact paths
        """
        checkpoint_id = str(uuid4())
        checkpoint_ts = datetime.now()
        
        # Auto-generate label if not provided
        if label is None:
            label = f"checkpoint-{checkpoint_ts.strftime('%Y%m%d-%H%M%S')}"
        
        # Create checkpoint artifact directory
        checkpoint_dir = self.artifact_root / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate identity components
        if identity_components is None:
            identity_components = {}
        
        required_components = [
            'instructions', 'calibration_params', 'skill_library',
            'classifier_weights', 'vector_store', 'meta_learning_policy',
            'failure_predictor'
        ]
        for component in required_components:
            if component not in identity_components:
                logger.warning(f"Component {component} not provided, will be empty")
        
        # Copy/store all 8 components
        component_paths = {}
        for component in required_components:
            if component in identity_components:
                source_path = identity_components[component]
                if source_path and source_path.exists():
                    dest_path = checkpoint_dir / component
                    if source_path.is_file():
                        shutil.copy2(source_path, dest_path)
                    elif source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    component_paths[component] = dest_path
                    logger.info(f"Copied {component} to {dest_path}")
            else:
                # Create placeholder for missing components
                dest_path = checkpoint_dir / component
                dest_path.touch()
                component_paths[component] = dest_path
        
        # Get parent checkpoint (most recent before this one)
        parent_checkpoint_id = await self._get_latest_checkpoint_id()
        
        # Generate change narrative by comparing with parent
        change_narrative = await self._generate_change_narrative(
            parent_checkpoint_id,
            checkpoint_id,
            component_paths,
        )
        
        # Use provided health snapshot or create default
        if health_snapshot is None:
            health_snapshot = SystemHealthSnapshot(
                calibration_error=0.0,
                dataset_coverage=0.0,
                skill_utilization=0.0,
                instruction_debt_days=0,
                failure_prediction_staleness_days=0,
            )
        
        # Create checkpoint object
        checkpoint = BehavioralCheckpoint(
            checkpoint_id=checkpoint_id,
            created_at=checkpoint_ts,
            label=label,
            change_narrative=change_narrative,
            instructions_path=component_paths.get('instructions', checkpoint_dir / 'instructions'),
            calibration_params_path=component_paths.get('calibration_params', checkpoint_dir / 'calibration_params'),
            skill_library_path=component_paths.get('skill_library', checkpoint_dir / 'skill_library'),
            classifier_weights_path=component_paths.get('classifier_weights', checkpoint_dir / 'classifier_weights'),
            vector_store_snapshot_path=component_paths.get('vector_store', checkpoint_dir / 'vector_store'),
            meta_learning_policy_path=component_paths.get('meta_learning_policy', checkpoint_dir / 'meta_learning_policy'),
            failure_predictor_path=component_paths.get('failure_predictor', checkpoint_dir / 'failure_predictor'),
            sft_dataset_hash=sft_dataset_hash or self._compute_empty_hash(),
            trigger=trigger,
            health_snapshot=health_snapshot,
            parent_checkpoint_id=parent_checkpoint_id,
        )
        
        # Store in database
        await self._store_checkpoint(checkpoint)
        
        logger.info(f"Created checkpoint {checkpoint_id} with label '{label}' (trigger: {trigger.value})")
        return checkpoint
    
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[BehavioralCheckpoint]:
        """Retrieve a checkpoint by ID."""
        query = """
            SELECT * FROM checkpoints WHERE id = ?
        """
        result = await self.db.fetch(query, (checkpoint_id,))
        if result:
            return self._row_to_checkpoint(result[0])
        return None
    
    async def list_checkpoints(self, limit: int = 100, offset: int = 0) -> List[BehavioralCheckpoint]:
        """List recent checkpoints with pagination."""
        query = """
            SELECT * FROM checkpoints
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        results = await self.db.fetch(query, (limit, offset))
        return [self._row_to_checkpoint(row) for row in results]
    
    async def get_checkpoint_history(self, days: int = 30) -> List[BehavioralCheckpoint]:
        """Get all checkpoints from last N days, in chronological order."""
        query = """
            SELECT * FROM checkpoints
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            ORDER BY created_at ASC
        """
        results = await self.db.fetch(query, (days,))
        return [self._row_to_checkpoint(row) for row in results]
    
    async def _get_latest_checkpoint_id(self) -> Optional[str]:
        """Get the ID of the most recent checkpoint."""
        query = "SELECT id FROM checkpoints ORDER BY created_at DESC LIMIT 1"
        result = await self.db.fetch(query)
        return result[0]['id'] if result else None
    
    async def _generate_change_narrative(
        self,
        prev_checkpoint_id: Optional[str],
        new_checkpoint_id: str,
        component_paths: Dict[str, Path],
    ) -> str:
        """
        Generate LLM-powered narrative of what changed.
        
        If no previous checkpoint, returns initialization narrative.
        Otherwise, compares components and generates explanation.
        """
        if not prev_checkpoint_id:
            return "Initial checkpoint created at system deployment."
        
        if not self.cloud_llm:
            return "No changes tracked (LLM client not configured)."
        
        # For MVP, return simple description. In production, use LLM.
        try:
            narrative = f"Checkpoint created. Components updated: {', '.join(component_paths.keys())}"
            # TODO: Integrate with LLM to generate semantic description
            return narrative
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return f"Checkpoint created (narrative generation failed: {e})"
    
    async def _store_checkpoint(self, checkpoint: BehavioralCheckpoint) -> None:
        """Store checkpoint metadata in database."""
        query = """
            INSERT INTO checkpoints (
                id, created_at, parent_id, label, trigger, change_narrative,
                health_snapshot_json,
                instructions_path, calibration_params_path, skill_library_path,
                classifier_weights_path, vector_store_snapshot_path,
                meta_learning_policy_path, failure_predictor_path, sft_dataset_hash,
                created_at_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        health_snapshot_json = json.dumps(asdict(checkpoint.health_snapshot), default=str)
        
        await self.db.execute(
            query,
            (
                checkpoint.checkpoint_id,
                checkpoint.created_at.isoformat(),
                checkpoint.parent_checkpoint_id,
                checkpoint.label,
                checkpoint.trigger.value,
                checkpoint.change_narrative,
                health_snapshot_json,
                str(checkpoint.instructions_path),
                str(checkpoint.calibration_params_path),
                str(checkpoint.skill_library_path),
                str(checkpoint.classifier_weights_path),
                str(checkpoint.vector_store_snapshot_path),
                str(checkpoint.meta_learning_policy_path),
                str(checkpoint.failure_predictor_path),
                checkpoint.sft_dataset_hash,
                checkpoint.created_at.timestamp(),
            )
        )
    
    def _row_to_checkpoint(self, row: Dict) -> BehavioralCheckpoint:
        """Convert database row to BehavioralCheckpoint object."""
        health_snapshot = SystemHealthSnapshot(**json.loads(row['health_snapshot_json']))
        
        return BehavioralCheckpoint(
            checkpoint_id=row['id'],
            created_at=datetime.fromisoformat(row['created_at']),
            label=row['label'],
            change_narrative=row['change_narrative'],
            instructions_path=Path(row['instructions_path']),
            calibration_params_path=Path(row['calibration_params_path']),
            skill_library_path=Path(row['skill_library_path']),
            classifier_weights_path=Path(row['classifier_weights_path']),
            vector_store_snapshot_path=Path(row['vector_store_snapshot_path']),
            meta_learning_policy_path=Path(row['meta_learning_policy_path']),
            failure_predictor_path=Path(row['failure_predictor_path']),
            sft_dataset_hash=row['sft_dataset_hash'],
            trigger=CheckpointTrigger(row['trigger']),
            health_snapshot=health_snapshot,
            parent_checkpoint_id=row['parent_id'],
        )
    
    @staticmethod
    def _compute_empty_hash() -> str:
        """Compute hash of empty dataset (for missing components)."""
        return hashlib.sha256(b'').hexdigest()
