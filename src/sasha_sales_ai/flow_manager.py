"""Flow manager for LangGraph workflows with Redis persistence"""

import logging
from typing import Optional, Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from .state import FlowState, FlowStatus, create_initial_state
from .graph import create_sales_graph
from .config import get_settings
from .storage.redis_store import RedisStateStore
from .utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.flow_manager")


def _get_checkpointer(redis_url: str):
    """Get the appropriate checkpointer based on configuration.
    
    Tries to use Redis checkpointer, falls back to memory if unavailable.
    
    Args:
        redis_url: Redis connection URL
        
    Returns:
        Checkpointer instance
    """
    try:
        from langgraph.checkpoint.redis import RedisSaver
        
        checkpointer = RedisSaver.from_conn_string(redis_url)
        checkpointer.setup()
        logger.info("Using Redis checkpointer for LangGraph")
        return checkpointer
    except ImportError:
        logger.warning(
            "langgraph-checkpoint-redis not installed, using MemorySaver. "
            "Install with: pip install langgraph-checkpoint-redis"
        )
        return MemorySaver()
    except Exception as e:
        logger.warning(f"Failed to initialize Redis checkpointer: {e}. Using MemorySaver.")
        return MemorySaver()


class FlowManager:
    """Manager for LangGraph workflow instances with Redis persistence.
    
    This manager handles:
    - Lead state persistence via Redis
    - LangGraph checkpointing via Redis
    - Graph execution and resumption
    - Approval workflow management
    """
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: Optional[str] = None,
    ):
        """Initialize the flow manager.
        
        Args:
            redis_url: Redis connection URL (uses config if not provided)
            key_prefix: Redis key prefix (uses config if not provided)
        """
        settings = get_settings()
        
        # Redis configuration
        self.redis_url = redis_url or settings.redis_url
        self.key_prefix = key_prefix or settings.redis_key_prefix
        
        # Initialize Redis state store for lead states
        self.state_store = RedisStateStore(
            redis_url=self.redis_url,
            key_prefix=self.key_prefix,
        )
        
        # Initialize checkpointer for LangGraph
        self.checkpointer = _get_checkpointer(self.redis_url)
        
        # Create the graph with checkpointer
        self.graph: CompiledStateGraph = create_sales_graph(
            checkpointer=self.checkpointer
        )
        
        # In-memory cache for performance (optional)
        self._cache: dict[str, FlowState] = {}
        
        logger.info(
            f"FlowManager initialized with Redis at {self.redis_url} "
            f"(prefix: {self.key_prefix})"
        )
    
    def get_state(self, lead_id: str) -> Optional[FlowState]:
        """Get the current state for a lead.
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            Current state or None if not found
        """
        # Check cache first
        if lead_id in self._cache:
            return self._cache[lead_id]
        
        # Fetch from Redis
        state = self.state_store.get(lead_id)
        if state:
            self._cache[lead_id] = state
        return state
    
    def _save_state(self, lead_id: str, state: FlowState) -> None:
        """Save state to Redis and update cache.
        
        Args:
            lead_id: Lead identifier
            state: State to save
        """
        self.state_store.set(lead_id, state)
        self._cache[lead_id] = state
        logger.debug(f"Saved state for lead {lead_id}")
    
    def _delete_state(self, lead_id: str) -> bool:
        """Delete state from Redis and cache.
        
        Args:
            lead_id: Lead identifier
            
        Returns:
            True if deleted
        """
        # Remove from cache
        if lead_id in self._cache:
            del self._cache[lead_id]
        
        # Remove from Redis
        return self.state_store.delete(lead_id)
    
    def get_or_create_state(
        self,
        lead_id: str,
        email_from: str = "",
        email_subject: str = "",
        email_body: str = "",
        email_type: str = "new",
    ) -> FlowState:
        """Get existing state or create a new one.
        
        Args:
            lead_id: Lead identifier
            email_from: Sender email address
            email_subject: Email subject
            email_body: Email body
            email_type: Type of email ("new" or "reply")
        
        Returns:
            FlowState for the lead
        """
        # Check for existing state
        state = self.get_state(lead_id)
        
        if state:
            # Update with new email data if provided
            if email_body:
                state["email_from"] = email_from
                state["email_subject"] = email_subject
                state["email_body"] = email_body
                state["email_type"] = email_type
                self._save_state(lead_id, state)
            return state
        
        # Create new state
        state = create_initial_state(
            lead_id=lead_id,
            email_from=email_from,
            email_subject=email_subject,
            email_body=email_body,
            email_type=email_type,
        )
        
        self._save_state(lead_id, state)
        
        return state
    
    async def run_flow(
        self,
        lead_id: str,
        state: FlowState,
        config: Optional[dict] = None,
    ) -> FlowState:
        """Run the flow for a lead.
        
        Args:
            lead_id: Lead identifier
            state: Initial or current state
            config: Optional additional configuration
        
        Returns:
            Updated state after flow execution
        """
        with get_tracing_context(
            name="run_sales_flow",
            tags=["flow_execution", lead_id],
            metadata={"lead_id": lead_id, "initial_status": state.get("status")},
        ):
            logger.info(f"Running flow for lead {lead_id}")
            
            thread_id = f"lead_{lead_id}"
            
            # Run the graph
            result = await self.graph.ainvoke(
                state,
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        **(config or {}),
                    }
                },
            )
            
            # Save state to Redis
            self._save_state(lead_id, result)
            
            logger.info(
                f"Flow completed for lead {lead_id}, status: {result.get('status')}"
            )
            
            return result
    
    def run_flow_sync(
        self,
        lead_id: str,
        state: FlowState,
        config: Optional[dict] = None,
    ) -> FlowState:
        """Run the flow synchronously.
        
        Args:
            lead_id: Lead identifier
            state: Initial or current state
            config: Optional additional configuration
        
        Returns:
            Updated state after flow execution
        """
        with get_tracing_context(
            name="run_sales_flow_sync",
            tags=["flow_execution", lead_id],
            metadata={"lead_id": lead_id, "initial_status": state.get("status")},
        ):
            logger.info(f"Running flow (sync) for lead {lead_id}")
            
            thread_id = f"lead_{lead_id}"
            
            # Run the graph synchronously
            result = self.graph.invoke(
                state,
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        **(config or {}),
                    }
                },
            )
            
            # Save state to Redis
            self._save_state(lead_id, result)
            
            logger.info(
                f"Flow completed for lead {lead_id}, status: {result.get('status')}"
            )
            
            return result
    
    async def resume_flow(
        self,
        lead_id: str,
        update_state: dict[str, Any],
    ) -> FlowState:
        """Resume an interrupted flow with updated state.
        
        Args:
            lead_id: Lead identifier
            update_state: State updates to apply before resuming
        
        Returns:
            Updated state after flow execution
        """
        with get_tracing_context(
            name="resume_flow",
            tags=["flow_resume", lead_id],
            metadata={"lead_id": lead_id, "updates": list(update_state.keys())},
        ):
            logger.info(f"Resuming flow for lead {lead_id}")
            
            thread_id = f"lead_{lead_id}"
            
            # Get current state from checkpointer
            current_state = await self.graph.aget_state(
                {"configurable": {"thread_id": thread_id}}
            )
            
            if current_state is None or current_state.values is None:
                # No checkpoint found, use Redis state
                redis_state = self.get_state(lead_id)
                if not redis_state:
                    raise ValueError(f"No state found for lead {lead_id}")
                current_values = redis_state
            else:
                current_values = dict(current_state.values)
            
            # Apply updates
            updated_state = {**current_values, **update_state}
            
            # Run from updated state
            result = await self.run_flow(lead_id, updated_state)
            
            return result
    
    def approve_lead(
        self,
        lead_id: str,
        approved_by: str = "system",
        notes: str = ""
    ) -> FlowState:
        """Approve a pending lead and resume flow.
        
        Args:
            lead_id: Lead identifier
            approved_by: Who approved
            notes: Approval notes
        
        Returns:
            Updated state after resuming
        """
        logger.info(f"Approving lead {lead_id}")
        
        state = self.get_state(lead_id)
        if not state:
            raise ValueError(f"Lead {lead_id} not found")
        
        if state.get("status") != FlowStatus.APPROVAL_PENDING:
            raise ValueError(f"Lead {lead_id} is not pending approval")
        
        # Update state with approval
        state["approved"] = True
        state["approval_notes"] = f"Approved by {approved_by}: {notes}"
        
        # Resume flow synchronously
        return self.run_flow_sync(lead_id, state)
    
    def reject_lead(
        self,
        lead_id: str,
        rejected_by: str = "system",
        reason: str = ""
    ) -> FlowState:
        """Reject a pending lead and resume flow.
        
        Args:
            lead_id: Lead identifier
            rejected_by: Who rejected
            reason: Rejection reason
        
        Returns:
            Updated state after resuming
        """
        logger.info(f"Rejecting lead {lead_id}")
        
        state = self.get_state(lead_id)
        if not state:
            raise ValueError(f"Lead {lead_id} not found")
        
        if state.get("status") != FlowStatus.APPROVAL_PENDING:
            raise ValueError(f"Lead {lead_id} is not pending approval")
        
        # Update state with rejection
        state["approved"] = False
        state["approval_notes"] = f"Rejected by {rejected_by}: {reason}"
        
        # Resume flow synchronously
        return self.run_flow_sync(lead_id, state)
    
    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead from storage.
        
        Args:
            lead_id: Lead identifier
            
        Returns:
            True if deleted
        """
        logger.info(f"Deleting lead {lead_id}")
        return self._delete_state(lead_id)
    
    def list_leads(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List all leads, optionally filtered by status.
        
        Args:
            status: Optional status filter
        
        Returns:
            List of lead summaries
        """
        return self.state_store.list_all(status=status)
    
    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get all leads pending approval.
        
        Returns:
            List of leads pending approval
        """
        return self.state_store.get_by_status(FlowStatus.APPROVAL_PENDING)
    
    def health_check(self) -> dict[str, Any]:
        """Check health of flow manager and its dependencies.
        
        Returns:
            Health status dictionary
        """
        redis_healthy = self.state_store.health_check()
        lead_count = self.state_store.count() if redis_healthy else 0
        
        return {
            "redis_connected": redis_healthy,
            "lead_count": lead_count,
            "checkpointer_type": type(self.checkpointer).__name__,
        }


# Global flow manager instance
_flow_manager: Optional[FlowManager] = None


def get_flow_manager() -> FlowManager:
    """Get or create the global flow manager instance.
    
    Returns:
        FlowManager instance
    """
    global _flow_manager
    if _flow_manager is None:
        _flow_manager = FlowManager()
    return _flow_manager


def reset_flow_manager() -> None:
    """Reset the global flow manager instance.
    
    Useful for testing or reconfiguration.
    """
    global _flow_manager
    _flow_manager = None
