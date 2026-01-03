"""Flow manager for LangGraph workflows"""

import json
import logging
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from .state import FlowState, FlowStatus, create_initial_state
from .graph import create_sales_graph
from .config import get_settings
from .utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.flow_manager")


class FlowManager:
    """Manager for LangGraph workflow instances and state persistence"""
    
    def __init__(
        self,
        state_storage_path: Optional[str] = None,
    ):
        """Initialize the flow manager.
        
        Args:
            state_storage_path: Path for state persistence
        """
        settings = get_settings()
        
        self.state_storage_path = Path(
            state_storage_path or settings.state_storage_path
        )
        self.state_storage_path.mkdir(parents=True, exist_ok=True)
        
        # Use memory checkpointer (can be upgraded to SQLite for persistence)
        self.checkpointer = MemorySaver()
        
        # Create the graph
        self.graph: CompiledStateGraph = create_sales_graph(
            checkpointer=self.checkpointer
        )
        
        # Cache for states
        self._states: dict[str, FlowState] = {}
        
        # Load existing states from disk
        self._load_existing_states()
        
        logger.info(f"FlowManager initialized with storage at {self.state_storage_path}")
    
    def _load_existing_states(self) -> None:
        """Load existing states from disk"""
        for state_file in self.state_storage_path.glob("*.json"):
            try:
                with open(state_file) as f:
                    state_data = json.load(f)
                    lead_id = state_data.get("lead_id")
                    if lead_id:
                        self._states[lead_id] = state_data
                        logger.debug(f"Loaded state for lead {lead_id}")
            except Exception as e:
                logger.warning(f"Failed to load state from {state_file}: {e}")
    
    def _save_state(self, lead_id: str, state: FlowState) -> None:
        """Save state to disk.
        
        Args:
            lead_id: Lead identifier
            state: State to save
        """
        state_file = self.state_storage_path / f"{lead_id}.json"
        
        # Add metadata
        state_with_meta = dict(state)
        state_with_meta["_updated_at"] = datetime.now().isoformat()
        
        with open(state_file, "w") as f:
            json.dump(state_with_meta, f, indent=2, default=str)
        
        self._states[lead_id] = state_with_meta
        logger.debug(f"Saved state for lead {lead_id}")
    
    def get_state(self, lead_id: str) -> Optional[FlowState]:
        """Get the current state for a lead.
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            Current state or None if not found
        """
        return self._states.get(lead_id)
    
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
        if lead_id in self._states:
            state = self._states[lead_id]
            # Update with new email data if provided
            if email_body:
                state["email_from"] = email_from
                state["email_subject"] = email_subject
                state["email_body"] = email_body
                state["email_type"] = email_type
            return state
        
        # Create new state
        state = create_initial_state(
            lead_id=lead_id,
            email_from=email_from,
            email_subject=email_subject,
            email_body=email_body,
            email_type=email_type,
        )
        
        self._states[lead_id] = state
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
            
            # Update and save state
            self._states[lead_id] = result
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
            
            # Update and save state
            self._states[lead_id] = result
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
                # No checkpoint found, use cached state
                if lead_id not in self._states:
                    raise ValueError(f"No state found for lead {lead_id}")
                current_values = self._states[lead_id]
            else:
                current_values = dict(current_state.values)
            
            # Apply updates
            updated_state = {**current_values, **update_state}
            
            # Run from updated state
            result = await self.run_flow(lead_id, updated_state)
            
            return result
    
    def approve_lead(self, lead_id: str, approved_by: str = "system", notes: str = "") -> FlowState:
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
    
    def reject_lead(self, lead_id: str, rejected_by: str = "system", reason: str = "") -> FlowState:
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
    
    def list_leads(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List all leads, optionally filtered by status.
        
        Args:
            status: Optional status filter
        
        Returns:
            List of lead summaries
        """
        leads = []
        
        for lead_id, state in self._states.items():
            if status and state.get("status") != status:
                continue
            
            leads.append({
                "lead_id": lead_id,
                "status": state.get("status"),
                "email_from": state.get("email_from"),
                "email_subject": state.get("email_subject"),
                "total_amount": state.get("total_amount"),
                "updated_at": state.get("_updated_at"),
            })
        
        return leads
    
    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get all leads pending approval.
        
        Returns:
            List of leads pending approval
        """
        return self.list_leads(status=FlowStatus.APPROVAL_PENDING)


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

