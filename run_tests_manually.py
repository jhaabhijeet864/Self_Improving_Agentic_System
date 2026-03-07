import asyncio
import os
import aiosqlite
from test_prompt_evolution import TEST_DB_PATH, test_initialize_population, test_get_active_prompt_selects_highest_yield, test_evolution_cycle_culls_and_breeds

async def setup():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except:
            pass
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

async def run_all():
    print("Running DB Setup...")
    await setup()
    print("Testing init...")
    await setup()
    await test_initialize_population()
    print("Testing active prompt...")
    await setup()
    await test_get_active_prompt_selects_highest_yield()
    print("Testing evo cycle...")
    await setup()
    await test_evolution_cycle_culls_and_breeds()
    print("ALL TESTS PASSED MANUALLY!")

if __name__ == "__main__":
    asyncio.run(run_all())
