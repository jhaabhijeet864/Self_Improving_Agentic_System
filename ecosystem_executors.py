"""
Ecosystem Executors - Wrappers for popular AI frameworks
Allows native execution of LangChain and LlamaIndex pipelines inside Jarvis-OS,
benefiting from our concurrency limits, timeouts, and self-optimization.
"""

import asyncio
from typing import Any, Dict, Optional, Union
import logging

from executor import Executor, TaskResult

logger = logging.getLogger(__name__)


class LangChainExecutor(Executor):
    """
    Executor wrapper specifically for LangChain runnables and chains.
    """
    
    async def execute_chain(
        self,
        chain: Any,
        inputs: Union[Dict[str, Any], str],
        task_id: Optional[str] = None,
        **kwargs
    ) -> TaskResult:
        """
        Execute a LangChain runnable asynchronously within Jarvis-OS.
        
        Args:
            chain: A LangChain Runnable (chain, agent, prompt template + model, etc.)
            inputs: The input dict or string expected by the chain
            task_id: Optional UUID
            kwargs: Additional invoke kwargs
        """
        async def _langchain_task():
            # Support unified modern invoke interface
            if hasattr(chain, "ainvoke"):
                return await chain.ainvoke(inputs, **kwargs)
            # Legacy async fallback
            elif hasattr(chain, "acall"):
                return await chain.acall(inputs, **kwargs)
            # Legacy sync fallback
            elif hasattr(chain, "invoke"):
                return await asyncio.to_thread(chain.invoke, inputs, **kwargs)
            else:
                return await asyncio.to_thread(chain.run, inputs, **kwargs)
                
        # Send it through the standard Executor pipeline for telemetry/timeout protection
        return await super().execute(_langchain_task, task_id=task_id)


class LlamaIndexExecutor(Executor):
    """
    Executor wrapper specifically for LlamaIndex query engines.
    """
    
    async def execute_query(
        self,
        query_engine: Any,
        query: str,
        task_id: Optional[str] = None,
        **kwargs
    ) -> TaskResult:
        """
        Execute a LlamaIndex query asynchronously within Jarvis-OS.
        
        Args:
            query_engine: A LlamaIndex BaseQueryEngine or similar
            query: The query string
            task_id: Optional UUID
            kwargs: Additional query kwargs
        """
        async def _llamaindex_task():
            if hasattr(query_engine, "aquery"):
                response = await query_engine.aquery(query)
                return str(response)
            else:
                response = await asyncio.to_thread(query_engine.query, query)
                return str(response)
                
        # Send it through the standard Executor pipeline
        return await super().execute(_llamaindex_task, task_id=task_id)
