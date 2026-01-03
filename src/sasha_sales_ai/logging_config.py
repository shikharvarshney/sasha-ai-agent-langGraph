"""LangSmith and Python logging configuration"""

import os
import logging
from typing import Optional, Any
from functools import wraps
from contextlib import contextmanager

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("sasha_sales_ai")


def setup_langsmith() -> Optional[Any]:
    """Initialize LangSmith client and configure tracing
    
    Returns:
        LangSmith Client instance or None if not configured
    """
    from langsmith import Client
    
    api_key = os.getenv("LANGSMITH_API_KEY")
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    
    if not api_key:
        logger.warning("LANGSMITH_API_KEY not set, tracing disabled")
        return None
    
    if not tracing_enabled:
        logger.info("LangSmith tracing is disabled via LANGSMITH_TRACING=false")
        return None
    
    try:
        client = Client(api_key=api_key)
        project = os.getenv("LANGSMITH_PROJECT", "sasha-ai-agent-langGraph")
        logger.info(f"LangSmith initialized for project: {project}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith: {e}")
        return None


@contextmanager
def get_tracing_context(
    name: str,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
    **kwargs,
):
    """Create a tracing context for custom operations
    
    Args:
        name: Name of the trace
        tags: Optional list of tags for the trace
        metadata: Optional metadata dictionary
        **kwargs: Additional arguments passed to tracing_context
    
    Yields:
        Tracing context manager
    """
    from langsmith.run_helpers import tracing_context
    
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    
    if not tracing_enabled:
        yield
        return
    
    with tracing_context(
        name=name,
        tags=tags or [],
        metadata=metadata or {},
        **kwargs,
    ):
        yield


def trace_function(
    name: Optional[str] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
):
    """Decorator to trace a function with LangSmith
    
    Args:
        name: Optional custom name for the trace (defaults to function name)
        tags: Optional list of tags for the trace
        metadata: Optional metadata dictionary
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            trace_name = name or func.__name__
            with get_tracing_context(
                name=trace_name,
                tags=tags,
                metadata=metadata,
            ):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace_name = name or func.__name__
            with get_tracing_context(
                name=trace_name,
                tags=tags,
                metadata=metadata,
            ):
                return await func(*args, **kwargs)
        
        if hasattr(func, "__wrapped__"):
            return async_wrapper
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


class LoggingCallback:
    """Callback handler for logging LangChain operations"""
    
    def __init__(self, logger_name: str = "sasha_sales_ai"):
        self.logger = logging.getLogger(logger_name)
    
    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs):
        chain_name = serialized.get("name", "Unknown")
        self.logger.info(f"Chain started: {chain_name}")
    
    def on_chain_end(self, outputs: dict, **kwargs):
        self.logger.info("Chain completed")
    
    def on_chain_error(self, error: Exception, **kwargs):
        self.logger.error(f"Chain error: {error}")
    
    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        self.logger.debug(f"LLM started with {len(prompts)} prompts")
    
    def on_llm_end(self, response, **kwargs):
        self.logger.debug("LLM completed")
    
    def on_llm_error(self, error: Exception, **kwargs):
        self.logger.error(f"LLM error: {error}")

