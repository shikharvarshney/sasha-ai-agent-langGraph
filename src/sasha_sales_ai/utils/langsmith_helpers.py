"""LangSmith utility functions"""

import os
import logging
from typing import Optional, Any
from functools import wraps
from contextlib import contextmanager

logger = logging.getLogger("sasha_sales_ai.utils.langsmith")


@contextmanager
def get_tracing_context(
    name: str,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
    **kwargs,
):
    """Create a tracing context for custom operations.
    
    This is a wrapper that gracefully handles cases where LangSmith
    is not configured or tracing is disabled.
    
    Args:
        name: Name of the trace
        tags: Optional list of tags for the trace
        metadata: Optional metadata dictionary
        **kwargs: Additional arguments passed to tracing_context
    
    Yields:
        Tracing context manager
    """
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    api_key = os.getenv("LANGSMITH_API_KEY")
    
    if not tracing_enabled or not api_key:
        yield
        return
    
    try:
        from langsmith.run_helpers import tracing_context
        
        with tracing_context(
            name=name,
            tags=tags or [],
            metadata=metadata or {},
            **kwargs,
        ):
            yield
    except ImportError:
        logger.warning("LangSmith not installed, tracing disabled")
        yield
    except Exception as e:
        logger.warning(f"LangSmith tracing error: {e}")
        yield


def trace_function(
    name: Optional[str] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
):
    """Decorator to trace a function with LangSmith.
    
    Args:
        name: Optional custom name for the trace (defaults to function name)
        tags: Optional list of tags for the trace
        metadata: Optional metadata dictionary
    
    Returns:
        Decorated function
    """
    def decorator(func):
        import asyncio
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
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
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_run_metadata(
    lead_id: str,
    node_name: str,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
) -> dict[str, Any]:
    """Create standardized metadata for LangSmith runs.
    
    Args:
        lead_id: The lead ID being processed
        node_name: Name of the current node/operation
        input_data: Optional input data summary
        output_data: Optional output data summary
    
    Returns:
        Metadata dictionary for LangSmith
    """
    metadata = {
        "lead_id": lead_id,
        "node": node_name,
        "project": os.getenv("LANGSMITH_PROJECT", "sasha-ai-agent-langGraph"),
    }
    
    if input_data:
        # Truncate large inputs for metadata
        metadata["input_summary"] = {
            k: str(v)[:200] if len(str(v)) > 200 else v
            for k, v in input_data.items()
        }
    
    if output_data:
        metadata["output_summary"] = {
            k: str(v)[:200] if len(str(v)) > 200 else v
            for k, v in output_data.items()
        }
    
    return metadata


def create_feedback(
    run_id: str,
    key: str,
    score: float,
    comment: Optional[str] = None,
) -> bool:
    """Create feedback for a LangSmith run.
    
    Args:
        run_id: The run ID to add feedback to
        key: Feedback key (e.g., "quality", "helpfulness")
        score: Score value (0-1)
        comment: Optional comment
    
    Returns:
        True if feedback was created successfully
    """
    api_key = os.getenv("LANGSMITH_API_KEY")
    
    if not api_key:
        logger.warning("Cannot create feedback: LANGSMITH_API_KEY not set")
        return False
    
    try:
        from langsmith import Client
        
        client = Client(api_key=api_key)
        client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment,
        )
        logger.info(f"Created feedback for run {run_id}: {key}={score}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to create feedback: {e}")
        return False

