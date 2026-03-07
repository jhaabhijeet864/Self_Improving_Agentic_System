import asyncio
from test_checkpoint_manager import (
    test_create_checkpoint_captures_all_eight_components,
    test_checkpoint_creation_with_different_triggers,
    test_get_checkpoint_by_id,
    test_list_checkpoints_with_pagination,
    test_checkpoint_history_linked_list,
    test_auto_generated_checkpoint_label,
    test_checkpoint_health_snapshot,
    test_checkpoint_with_missing_components,
    test_checkpoint_serialization
)

async def run_all():
    print("Testing capture...")
    await test_create_checkpoint_captures_all_eight_components()
    print("Testing triggers...")
    await test_checkpoint_creation_with_different_triggers()
    print("Testing get by ID...")
    await test_get_checkpoint_by_id()
    print("Testing pagination...")
    await test_list_checkpoints_with_pagination()
    print("Testing history linked list...")
    await test_checkpoint_history_linked_list()
    print("Testing auto labels...")
    await test_auto_generated_checkpoint_label()
    print("Testing health snapshot...")
    await test_checkpoint_health_snapshot()
    print("Testing missing components...")
    await test_checkpoint_with_missing_components()
    print("Testing serialization...")
    await test_checkpoint_serialization()
    print("ALL CHECKPOINT TESTS PASSED MANUALLY!")

if __name__ == "__main__":
    asyncio.run(run_all())
