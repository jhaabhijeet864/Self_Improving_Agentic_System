"""
Comprehensive test suite for Jarvis-OS
Tests all core components
"""

import asyncio
import pytest
import time
import tempfile
import os
from executor import Executor, TaskStatus
from autopsy import Autopsy, LogEntry
from mutation import Mutation
from memory_manager import MemoryManager
from fast_router import FastRouter, TaskPriority
from structured_logger import StructuredLogger
from jarvis_os import JarvisOS, AgentConfig


class TestExecutor:
    """Tests for Executor component"""
    
    @pytest.fixture
    def executor(self):
        return Executor(max_workers=5, timeout=10.0)
    
    @pytest.mark.asyncio
    async def test_execute_simple_task(self, executor):
        """Test executing a simple task"""
        async def simple_task():
            return "success"
        
        result = await executor.execute(simple_task)
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_task_with_timeout(self, executor):
        """Test task timeout handling"""
        executor.timeout = 0.1
        
        async def slow_task():
            await asyncio.sleep(1.0)
        
        result = await executor.execute(slow_task)
        assert result.status == TaskStatus.FAILED
        assert "timeout" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_batch_tasks(self, executor):
        """Test batch execution"""
        async def task1():
            return 1
        
        async def task2():
            return 2
        
        tasks = {
            "task1": (task1, (), {}),
            "task2": (task2, (), {}),
        }
        
        results = await executor.execute_batch(tasks)
        assert len(results) == 2
        assert results["task1"].result == 1
        assert results["task2"].result == 2
    
    def test_performance_stats(self, executor):
        """Test performance statistics"""
        stats = executor.get_performance_stats()
        assert stats["total_tasks"] == 0
        assert stats["completed"] == 0


class TestAutopsy:
    """Tests for Autopsy component"""
    
    @pytest.fixture
    def autopsy(self):
        return Autopsy(max_entries=100)
    
    def test_add_log(self, autopsy):
        """Test adding log entries"""
        entry = LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="Test",
            task_id="task1",
            duration=1.0,
        )
        autopsy.add_log(entry)
        assert len(autopsy.logs) == 1
    
    def test_error_rate(self, autopsy):
        """Test error rate calculation"""
        autopsy.add_log(LogEntry(
            timestamp=time.time(),
            level="INFO",
            message="OK",
        ))
        autopsy.add_log(LogEntry(
            timestamp=time.time(),
            level="ERROR",
            message="Failed",
            error="Test error",
        ))
        
        error_rate = autopsy.get_error_rate()
        assert error_rate == 0.5
    
    def test_identify_error_patterns(self, autopsy):
        """Test error pattern identification"""
        for i in range(5):
            autopsy.add_log(LogEntry(
                timestamp=time.time(),
                level="ERROR",
                message="Failed",
                error="Network timeout",
            ))
        
        patterns = autopsy.identify_error_patterns()
        assert len(patterns) == 1
        assert patterns[0]["error"] == "Network timeout"
        assert patterns[0]["frequency"] == 5


class TestMutation:
    """Tests for Mutation component"""
    
    @pytest.fixture
    def mutation(self):
        return Mutation()
    
    def test_generate_update(self, mutation):
        """Test generating an update"""
        update = mutation.generate_update(
            category="test",
            priority="high",
            description="Test update",
            new_instruction={"name": "test", "value": 1},
            reasoning="For testing",
            confidence_score=0.9,
        )
        
        assert update.category == "test"
        assert update.priority == "high"
        assert update.confidence_score == 0.9
    
    def test_apply_update(self, mutation):
        """Test applying an update"""
        update = mutation.generate_update(
            category="test",
            priority="medium",
            description="Test",
            new_instruction={"name": "test_instr", "value": 42},
            reasoning="Testing",
        )
        
        result = mutation.apply_update(update)
        assert result is True
        assert update.applied is True
    
    def test_rollback_update(self, mutation):
        """Test rolling back an update"""
        update = mutation.generate_update(
            category="test",
            priority="low",
            description="Test rollback",
            new_instruction={"name": "test", "value": 1},
            reasoning="Testing",
            old_instruction={"name": "test", "value": 0},
        )
        
        mutation.apply_update(update)
        result = mutation.rollback_update(update.id)
        assert result is True


class TestMemoryManager:
    """Tests for Memory Manager"""
    
    @pytest.fixture
    def memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_file = os.path.join(tmpdir, "memory.json")
            yield MemoryManager(short_term_size=100, long_term_file=storage_file)
    
    def test_store_and_retrieve(self, memory):
        """Test storing and retrieving values"""
        memory.store("key1", "value1", persistent=False)
        value = memory.retrieve("key1")
        assert value == "value1"
    
    def test_memory_ttl(self, memory):
        """Test time-to-live"""
        memory.store("key1", "value1", ttl=0.1)
        time.sleep(0.2)
        value = memory.retrieve("key1")
        assert value is None


class TestFastRouter:
    """Tests for Fast Router"""
    
    @pytest.fixture
    def router(self):
        return FastRouter()
    
    def test_route_task(self, router):
        """Test basic task routing"""
        # Need to register an executor first
        router.register_executor("default", None)
        
        executor_id, priority = router.route_task(
            "test_task",
            {},
            TaskPriority.NORMAL,
        )
        
        assert executor_id == "default"


class TestStructuredLogger:
    """Tests for Structured Logger"""
    
    def test_logger_initialization(self):
        """Test logger creation"""
        logger = StructuredLogger("test_logger", "INFO")
        assert logger.logger.name == "test_logger"
    
    def test_log_task_start(self):
        """Test logging task start"""
        logger = StructuredLogger("test", "INFO")
        logger.log_task_start("task1", "compute", {})
        # No exception = success


class TestJarvisOS:
    """Tests for main JarvisOS agent"""
    
    @pytest.fixture
    def agent(self):
        config = AgentConfig(
            name="test-agent",
            max_workers=5,
            task_timeout=10.0,
        )
        return JarvisOS(config)
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, agent):
        """Test agent start and stop"""
        await agent.start()
        assert agent.running is True
        
        await agent.stop()
        assert agent.running is False
    
    @pytest.mark.asyncio
    async def test_execute_task(self, agent):
        """Test task execution"""
        await agent.start()
        
        async def test_task():
            return "test_result"
        
        result = await agent.execute_task(
            task_type="test",
            task_func=test_task,
        )
        
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "test_result"
        
        await agent.stop()
    
    def test_agent_status(self, agent):
        """Test getting agent status"""
        status = agent.get_status()
        assert status["name"] == "test-agent"
        assert status["running"] is False


@pytest.mark.asyncio
async def test_full_workflow():
    """Integration test for full workflow"""
    
    config = AgentConfig(
        name="integration-agent",
        max_workers=5,
        task_timeout=30.0,
        auto_optimize=False,
    )
    
    agent = JarvisOS(config)
    await agent.start()
    
    # Execute some tasks
    async def work_task(n):
        await asyncio.sleep(0.01)
        return n * 2
    
    for i in range(10):
        result = await agent.execute_task(
            task_type="work",
            task_func=work_task,
            task_params={"args": [i]},
        )
        assert result.result == i * 2
    
    # Check metrics
    metrics = agent.get_metrics()
    assert metrics["performance"]["total_tasks"] == 10
    
    await agent.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
