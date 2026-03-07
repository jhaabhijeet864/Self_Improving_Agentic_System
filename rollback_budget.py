import asyncio
import logging
from typing import Dict, Any
from impact_reporter import ImpactReporter
from mutation import Mutation
from jarvis_common.events import JarvisEvent, EventType
from ipc_server import IPCBridgeServer

logger = logging.getLogger(__name__)

class RollbackBudget:
    """
    Phase 6: Rollback Budget
    A background policy engine that checks for degradation and triggers automatic rollbacks.
    """
    def __init__(self, db, mutation_engine: Mutation, ipc_server: IPCBridgeServer, check_interval: int = 1800):
        self.db = db
        self.mutation_engine = mutation_engine
        self.ipc_server = ipc_server
        self.check_interval = check_interval
        self.reporter = ImpactReporter(db)
        self.running = False
        
    async def start(self):
        self.running = True
        logger.info("Started Rollback Budget background task.")
        while self.running:
            try:
                await self._check_mutations()
            except Exception as e:
                logger.error(f"Error in RollbackBudget check: {e}")
            await asyncio.sleep(self.check_interval)
            
    def stop(self):
        self.running = False

    async def _check_mutations(self):
        # Find recently applied mutations.
        # For simplicity, let's mock checking recent mutations.
        recent_mutations = [m for m in self.mutation_engine.update_history if m.applied]
        
        for mut in recent_mutations:
            # Mock querying DB for stats
            # In reality, you'd calculate pre-mutation and post-mutation success rates.
            pre_stats = {"success_rate": 0.90, "avg_latency": 0.5}
            post_stats = {"success_rate": 0.82, "avg_latency": 0.8} # Simulated degradation
            
            # If success rate dropped more than 5% (0.05)
            if post_stats["success_rate"] < pre_stats["success_rate"] - 0.05:
                logger.warning(f"Statistically significant degradation detected for mutation {mut.id}!")
                
                # Auto Rollback
                rollback_success = self.mutation_engine.rollback_update(mut.id)
                if rollback_success:
                    logger.info(f"Successfully auto-rolled back mutation {mut.id}")
                    
                    # Notify Jarvis
                    await self.ipc_server.send_directive(
                        # Assuming a standard directive or event payload
                        # We send a standard Event
                        JarvisEvent(
                            event_id=f"rb_{mut.id}",
                            event_type=EventType.MUTATION_APPLIED,
                            source="self_improver",
                            payload={"action": "rolled_back", "mutation_id": mut.id}
                        )
                    )
                    
                    # Generate report
                    await self.reporter.generate_report(mut.id, pre_stats, post_stats)
