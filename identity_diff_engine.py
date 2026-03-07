"""
IdentityDiffEngine - Fifth Chapter: Identity (Phase 2)

Calculates the semantic distance, classifier drift, and generates
behavioral deltas across the 8 components between two checkpoints.
It relies on evaluating a simulated 540-record regression suite for Semantic Distance.
"""

import asyncio
import json
import logging
import uuid
import difflib
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from checkpoint_manager import CheckpointManager, BehavioralCheckpoint

logger = logging.getLogger(__name__)


@dataclass
class BehavioralDiff:
    """Represents the semantic diff between two checkpoints."""
    diff_id: str
    checkpoint_a_id: str
    checkpoint_b_id: str
    semantic_distance: int  # 0 to 540
    instruction_delta: Dict[str, Any]
    calibration_delta: Dict[str, Any]
    skill_delta: Dict[str, Any]
    classifier_drift: float  # 0.0 to 1.0
    narrative: str
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Serialize diff to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


class IdentityDiffEngine:
    """
    Computes differences between two system checkpoints.
    
    Responsibilities:
    - Load component artifacts from CheckpointManager.
    - Evaluate Semantic Distance (simulated 540 suite metric).
    - Provide instruction diffs, calibration diffs, and skill diffs.
    - Compute Classifier drift via mock cosine similarity.
    - Generate LLM narrative to contextualize the change.
    - Save diffs to the checkpoint_diffs database schema.
    """

    def __init__(
        self,
        db,
        checkpoint_manager: CheckpointManager,
        cloud_llm_client=None
    ):
        """
        Initialize the diff engine.
        
        Args:
            db: Database connection (async SQLite)
            checkpoint_manager: For retrieving actual checkpoint artifacts.
            cloud_llm_client: Client for cloud LLM to summarize diff narrative.
        """
        self.db = db
        self.cm = checkpoint_manager
        self.cloud_llm = cloud_llm_client

    async def compute_diff(self, checkpoint_a_id: str, checkpoint_b_id: str) -> BehavioralDiff:
        """
        Compute and store the difference between two checkpoints.
        
        Args:
            checkpoint_a_id: The base checkpoint ID.
            checkpoint_b_id: The new checkpoint ID to compare.
            
        Returns:
            BehavioralDiff representing the calculated drift and changes.
        """
        ckpt_a = await self.cm.get_checkpoint(checkpoint_a_id)
        ckpt_b = await self.cm.get_checkpoint(checkpoint_b_id)

        if not ckpt_a or not ckpt_b:
            raise ValueError("One or both checkpoints could not be found.")

        # 1. Compute Instruction Deltas
        instruction_delta = self._compute_text_diff(
            ckpt_a.instructions_path, 
            ckpt_b.instructions_path
        )

        # 2. Compute Calibration Deltas
        calibration_delta = self._compute_json_delta(
            ckpt_a.calibration_params_path,
            ckpt_b.calibration_params_path
        )

        # 3. Compute Skill Deltas
        skill_delta = self._compute_json_delta(
            ckpt_a.skill_library_path,
            ckpt_b.skill_library_path
        )

        # 4. Synthesize Semantics & Drifts
        # Provide a synthetic mapping based on file path diffs in MVP
        # In full production this executes the 540-record tests
        lines_changed = len(instruction_delta.get("diff", []))
        semantic_distance = min(540, lines_changed * 2) 

        classifier_drift = 0.0
        if not ckpt_a.classifier_weights_path.read_bytes() == ckpt_b.classifier_weights_path.read_bytes():
             # Provide arbitrary mock value for drift if binary bytes mismatch MVP
             classifier_drift = 0.15 

        # 5. Generate Narrative
        narrative = await self._generate_diff_narrative(
            semantic_distance, 
            instruction_delta, 
            calibration_delta, 
            skill_delta
        )

        diff = BehavioralDiff(
            diff_id=str(uuid.uuid4()),
            checkpoint_a_id=checkpoint_a_id,
            checkpoint_b_id=checkpoint_b_id,
            semantic_distance=semantic_distance,
            instruction_delta=instruction_delta,
            calibration_delta=calibration_delta,
            skill_delta=skill_delta,
            classifier_drift=classifier_drift,
            narrative=narrative,
            created_at=datetime.now()
        )

        # 6. Store in Database
        await self._store_diff(diff)
        
        logger.info(f"Computed Identity Diff {diff.diff_id} between A ({checkpoint_a_id}) and B ({checkpoint_b_id})")
        return diff

    async def get_diff(self, checkpoint_a_id: str, checkpoint_b_id: str) -> Optional[BehavioralDiff]:
        """Fetch previously computed diff from the database."""
        query = "SELECT * FROM checkpoint_diffs WHERE checkpoint_a_id = ? AND checkpoint_b_id = ?"
        result = await self.db.fetch(query, (checkpoint_a_id, checkpoint_b_id))
        if result:
            return self._row_to_diff(result[0])
        return None

    def _compute_text_diff(self, path_a: Path, path_b: Path) -> Dict[str, Any]:
        """Generate a basic line diff between texts if they exist."""
        text_a = path_a.read_text(errors="ignore") if path_a.exists() else ""
        text_b = path_b.read_text(errors="ignore") if path_b.exists() else ""
        
        if text_a == text_b:
            return {"changed": False, "diff": []}

        lines_a = text_a.splitlines()
        lines_b = text_b.splitlines()
        diff_lines = list(difflib.unified_diff(lines_a, lines_b, n=2))
        return {
            "changed": True,
            "diff_length": len(diff_lines),
            "diff": diff_lines[:50],  # truncated for JSON constraints
            "added_lines": sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++')),
            "removed_lines": sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))
        }

    def _compute_json_delta(self, path_a: Path, path_b: Path) -> Dict[str, Any]:
        """Compare two JSON dictionaries dynamically if parsing allows."""
        def load_json(p: Path):
            if not p.exists():
                return {}
            try:
                return json.loads(p.read_text())
            except:
                return {}

        data_a = load_json(path_a)
        data_b = load_json(path_b)
        
        # Simple Key Difference logic for MVP
        keys_a = set(data_a.keys())
        keys_b = set(data_b.keys())
        
        added = list(keys_b - keys_a)
        removed = list(keys_a - keys_b)
        
        changed = []
        for k in keys_a.intersection(keys_b):
            if data_a[k] != data_b[k]:
                changed.append(k)

        is_changed = bool(added or removed or changed)
        return {
            "changed": is_changed,
            "added_keys": added,
            "removed_keys": removed,
            "modified_keys": changed
        }

    async def _generate_diff_narrative(
        self,
        semantic_dist: int,
        instruct_delta: Dict,
        calib_delta: Dict,
        skill_delta: Dict
    ) -> str:
        """Use LLM to explain the delta. Mocked for raw operations."""
        if not self.cloud_llm:
            return f"Identity drifted by {semantic_dist}/540 points. Instructions Changed: {instruct_delta['changed']}."
        
        try:
            # LLM would actually be invoked here to summarize the json fields.
            return f"LLM Narrative: System behavior mutated by {semantic_dist} vectors based on {instruct_delta.get('added_lines',0)} line additions."
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return f"Diff Narrative generation failed."

    async def _store_diff(self, diff: BehavioralDiff) -> None:
        """Insert diff object into Database."""
        query = """
            INSERT INTO checkpoint_diffs (
                id, checkpoint_a_id, checkpoint_b_id, semantic_distance,
                instruction_delta_json, calibration_delta_json, skill_delta_json,
                classifier_drift, narrative, created_at, created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            query,
            (
                diff.diff_id,
                diff.checkpoint_a_id,
                diff.checkpoint_b_id,
                diff.semantic_distance,
                json.dumps(diff.instruction_delta),
                json.dumps(diff.calibration_delta),
                json.dumps(diff.skill_delta),
                diff.classifier_drift,
                diff.narrative,
                diff.created_at.isoformat(),
                diff.created_at.timestamp()
            )
        )

    def _row_to_diff(self, row: Dict) -> BehavioralDiff:
        """Deserialize SQL row into BehavioralDiff struct."""
        return BehavioralDiff(
            diff_id=row['id'],
            checkpoint_a_id=row['checkpoint_a_id'],
            checkpoint_b_id=row['checkpoint_b_id'],
            semantic_distance=row['semantic_distance'],
            instruction_delta=json.loads(row['instruction_delta_json']),
            calibration_delta=json.loads(row['calibration_delta_json']),
            skill_delta=json.loads(row['skill_delta_json']),
            classifier_drift=row['classifier_drift'],
            narrative=row['narrative'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
