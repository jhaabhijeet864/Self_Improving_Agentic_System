"""
Jarvis-OS: A Production-Scale AI Agent Framework
Version 1.0.0

An autonomous, self-improving AI agent with concurrent task execution,
advanced memory management, and continuous optimization.
"""

__version__ = "1.0.0"
__author__ = "Jarvis Development Team"
__license__ = "MIT"

# Import main components for easy access
from .executor import Executor, TaskStatus, TaskResult
from .autopsy import Autopsy, LogEntry, AnalysisResult
from .mutation import Mutation, InstructionUpdate
from .memory_manager import MemoryManager, ShortTermMemory, LongTermMemory
from .fast_router import FastRouter, TaskPriority, ConditionalRouter
from .structured_logger import StructuredLogger
from .jarvis_os import JarvisOS, AgentConfig

__all__ = [
    'Executor',
    'TaskStatus',
    'TaskResult',
    'Autopsy',
    'LogEntry',
    'AnalysisResult',
    'Mutation',
    'InstructionUpdate',
    'MemoryManager',
    'ShortTermMemory',
    'LongTermMemory',
    'FastRouter',
    'TaskPriority',
    'ConditionalRouter',
    'StructuredLogger',
    'JarvisOS',
    'AgentConfig',
]
