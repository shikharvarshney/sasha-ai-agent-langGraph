"""Error handling node - stops flow without sending emails."""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..utils.state_logger import log_state_before, log_state_after

logger = logging.getLogger("sasha_sales_ai.nodes.error_handler")


def handle_error(state: FlowState) -> dict[str, Any]:
    """Handle errors by stopping the flow gracefully.
    
    This node:
    1. Logs the error details
    2. Does NOT send any email to the customer
    3. Marks the flow as ERROR status
    
    CRITICAL: This node should NEVER send emails with incomplete/wrong info.
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields with error status
    """
    lead_id = state.get("lead_id", "unknown")
    error_message = state.get("error_message", "Unknown error")
    error_node = state.get("error_node", "unknown")
    
    # Log state before execution
    log_state_before("handle_error", state)
    
    logger.error(
        f"ERROR HANDLER: Lead {lead_id} - Error in {error_node}: {error_message}"
    )
    logger.error(
        f"FLOW STOPPED - No email will be sent to customer with incomplete/wrong info"
    )
    
    result = {
        "status": FlowStatus.ERROR,
        "current_node": "handle_error",
        # Explicitly ensure no outgoing email
        "outgoing_email_subject": "",
        "outgoing_email_body": "",
    }
    
    log_state_after("handle_error", state, result)
    return result

