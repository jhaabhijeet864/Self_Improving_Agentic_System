import pytest
import aiosqlite
import uuid
import os
from unittest.mock import AsyncMock
from prompt_evolution import PromptEvolutionEngine
from jarvis_common.schemas import PromptVariant

TEST_DB_PATH = "test_jarvis_state.db"

# Override the DB_PATH for testing
import prompt_evolution
prompt_evolution.DB_PATH = TEST_DB_PATH

class MockLLM:
    async def call(self, prompt: str) -> str:
        return "MOCKED OFFSPRING PROMPT"

@pytest.fixture(autouse=True)
async def setup_test_db():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS prompt_variants (
                variant_id TEXT PRIMARY KEY,
                prompt_text TEXT NOT NULL,
                generation INTEGER NOT NULL,
                parent_a_id TEXT,
                parent_b_id TEXT,
                mutations_generated INTEGER DEFAULT 0,
                mutations_promoted INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

@pytest.mark.asyncio
async def test_initialize_population():
    engine = PromptEvolutionEngine(MockLLM())
    seeds = ["Prompt A", "Prompt B", "Prompt C", "Prompt D", "Prompt E"]
    
    await engine.initialize_population(seeds)
    
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM prompt_variants")
        count = (await cursor.fetchone())[0]
        assert count == 5

@pytest.mark.asyncio
async def test_get_active_prompt_selects_highest_yield():
    engine = PromptEvolutionEngine(MockLLM())
    
    # Insert 2 variants. Make one strictly better.
    v1 = PromptVariant(prompt_text="A", generation=0, mutations_generated=10, mutations_promoted=2) # 20%
    v2 = PromptVariant(prompt_text="B", generation=0, mutations_generated=10, mutations_promoted=8) # 80%
    
    await engine._save_variant(v1)
    await engine._save_variant(v2)
    
    # Due to 20% epsilon, it might sometimes pick v1, but we can force it or just check it usually picks v2
    # To be deterministic, we'll patch random.random
    import random
    original_random = random.random
    random.random = lambda: 0.5  # bypass epsilon
    
    selected = await engine.get_active_prompt()
    assert selected.variant_id == v2.variant_id
    
    random.random = original_random

@pytest.mark.asyncio
async def test_evolution_cycle_culls_and_breeds():
    mock_llm = MockLLM()
    # Spy on the LLM call
    mock_llm.call = AsyncMock(return_value="Crossbred offspring!")
    engine = PromptEvolutionEngine(mock_llm)
    
    # We create 5 variants. 
    # V1, V2, V3  are good. (High yield)
    # V4, V5 are bad. (Low yield)
    variants = [
        PromptVariant(prompt_text="V1", generation=0, mutations_generated=20, mutations_promoted=18), # 90%
        PromptVariant(prompt_text="V2", generation=0, mutations_generated=20, mutations_promoted=16), # 80%
        PromptVariant(prompt_text="V3", generation=0, mutations_generated=20, mutations_promoted=10), # 50%
        PromptVariant(prompt_text="V4", generation=0, mutations_generated=20, mutations_promoted=2),  # 10%
        PromptVariant(prompt_text="V5", generation=0, mutations_generated=20, mutations_promoted=0),  # 0%
    ]
    
    for v in variants:
        await engine._save_variant(v)
        
    await engine.evolve_population(min_evals_required=10)
    
    async with aiosqlite.connect(TEST_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Check that V4 and V5 were culled (is_active = 0)
        cursor = await db.execute("SELECT is_active, prompt_text FROM prompt_variants WHERE prompt_text IN ('V4', 'V5')")
        culled_rows = await cursor.fetchall()
        for r in culled_rows:
            assert r["is_active"] == 0
            
        # Check that offspring were created (generation = 1)
        cursor = await db.execute("SELECT * FROM prompt_variants WHERE generation = 1")
        offspring_rows = await cursor.fetchall()
        
        # Culling rate is 40% (2 out of 5), so 2 offspring should be generated to replace them
        assert len(offspring_rows) == 2
        for r in offspring_rows:
            assert r["prompt_text"] == "Crossbred offspring!"
            assert r["is_active"] == 1
            # They should be children of V1 and V2
            assert r["parent_a_id"] == variants[0].variant_id
            assert r["parent_b_id"] == variants[1].variant_id
            
    assert mock_llm.call.call_count == 2
