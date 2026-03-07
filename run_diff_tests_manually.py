import asyncio
from test_identity_diff_engine import test_identity_diff_engine_computes_deltas

async def run_all():
    print("Testing IdentityDiffEngine...")
    await test_identity_diff_engine_computes_deltas()
    print("ALL IDENTITY DIFF TESTS PASSED MANUALLY!")

if __name__ == "__main__":
    asyncio.run(run_all())
