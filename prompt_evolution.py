import random
import uuid
import aiosqlite
from datetime import datetime
from jarvis_common.schemas import PromptVariant
from database import DB_PATH

class PromptEvolutionEngine:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.population_size = 5
        self.culling_rate = 0.4  # Bottom 40% (2 out of 5) get culled

    async def _save_variant(self, variant: PromptVariant):
        """Helper to save a variant to the DB."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO prompt_variants (
                    variant_id, prompt_text, generation, parent_a_id, parent_b_id, 
                    mutations_generated, mutations_promoted, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    variant.variant_id, variant.prompt_text, variant.generation, 
                    variant.parent_a_id, variant.parent_b_id,
                    variant.mutations_generated, variant.mutations_promoted, 
                    variant.is_active, variant.created_at
                )
            )
            await db.commit()

    async def initialize_population(self, seed_prompts: list[str]):
        """Populate the database with generation 0 if empty."""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM prompt_variants WHERE is_active = 1")
            count = (await cursor.fetchone())[0]
            
            if count == 0:
                for text in seed_prompts[:self.population_size]:
                    v = PromptVariant(prompt_text=text, generation=0)
                    await self._save_variant(v)

    async def get_active_prompt(self) -> PromptVariant:
        """
        Uses greedy or epsilon-greedy selection to pick a prompt variant
        from the currently active population for use in a Self-Critique cycle.
        """
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM prompt_variants WHERE is_active = 1")
            rows = await cursor.fetchall()
            
            if not rows:
                return None
                
            variants = [PromptVariant(**dict(row)) for row in rows]
            
            # Epsilon-greedy: 20% random exploration, 80% highest yield rate
            if random.random() < 0.2:
                return random.choice(variants)
            else:
                return max(variants, key=lambda v: v.yield_rate)

    async def record_mutation_generated(self, variant_id: str):
        """Increment the mutations_generated counter."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE prompt_variants SET mutations_generated = mutations_generated + 1 WHERE variant_id = ?",
                (variant_id,)
            )
            await db.commit()

    async def record_mutation_promoted(self, variant_id: str):
        """Increment the mutations_promoted counter (called post A/B test win)."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE prompt_variants SET mutations_promoted = mutations_promoted + 1 WHERE variant_id = ?",
                (variant_id,)
            )
            await db.commit()

    async def evolve_population(self, min_evals_required=10):
        """
        The Genetic Algorithm:
        1. Fetch all active variants.
        2. Filter to variants that have enough evaluations (`min_evals_required`). If not all have enough, abort.
        3. Culling: Disable the lowest performing variants (is_active = 0).
        4. Reproduction: Select the top 2 as parents.
        5. Invoke LLM to perform crossover/mutation on parents to generate offspring.
        6. Save new offspring (generation N+1) to the database as active.
        """
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM prompt_variants WHERE is_active = 1")
            rows = await cursor.fetchall()
            
            if len(rows) < self.population_size:
                return # Not enough variants to evolve yet
                
            variants = [PromptVariant(**dict(row)) for row in rows]
            
            # Ensure population is mature enough to run an evolutionary cycle
            for v in variants:
                if v.mutations_generated < min_evals_required:
                    return # Still accumulating data on current generation
                    
            # Sort by yield rate descending
            sorted_variants = sorted(variants, key=lambda v: v.yield_rate, reverse=True)
            
            cull_count = int(self.population_size * self.culling_rate)
            survivors = sorted_variants[:-cull_count]
            culled = sorted_variants[-cull_count:]
            
            # 1. Cull the losers
            for v in culled:
                await db.execute("UPDATE prompt_variants SET is_active = 0 WHERE variant_id = ?", (v.variant_id,))
            await db.commit()
            
            # 2. Reproduce: Top 2 become parents
            if len(survivors) >= 2:
                parent_a, parent_b = survivors[0], survivors[1]
                
                # Breed new offspring to replace the culled ones
                for _ in range(cull_count):
                    new_generation = max(parent_a.generation, parent_b.generation) + 1
                    
                    llm_instruction = f"""
These two prompts generated the highest percentage of successful system updates. 
Combine their structural strengths to generate a mutated third variant meant to critique AI system failures.
Output ONLY the newly generated text.

PARENT A:
{parent_a.prompt_text}

PARENT B:
{parent_b.prompt_text}
"""
                    
                    # Call the cloud LLM to perform crossover/mutation
                    mutated_text = await self.llm.call(llm_instruction)
                    
                    offspring = PromptVariant(
                        prompt_text=mutated_text.strip(),
                        generation=new_generation,
                        parent_a_id=parent_a.variant_id,
                        parent_b_id=parent_b.variant_id
                    )
                    
                    await self._save_variant(offspring)
