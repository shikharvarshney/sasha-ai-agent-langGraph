"""Rejection handling node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..chains.email_writer import write_rejection_email
from ..tools.email_tool import send_email
from ..storage.rag_storage import get_rag_storage
from ..utils.langsmith_helpers import get_tracing_context
from ..utils.state_logger import log_state_before, log_state_after, log_outgoing_email

logger = logging.getLogger("sasha_sales_ai.nodes.rejection")


def handle_rejection(state: FlowState) -> dict[str, Any]:
    """Handle a rejected request or infeasible order.
    
    This node:
    1. Determines the rejection reason
    2. Generates a professional rejection email with alternatives
    3. Sends the email to the customer
    4. Marks the flow as completed (rejected)
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    # Log state before execution
    log_state_before("handle_rejection", state)
    
    with get_tracing_context(
        name="handle_rejection",
        tags=["node", "rejection", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Handling rejection for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            
            customer_name = requirements.get("customer_name", "")
            customer_email = state.get("email_from", "")
            
            # Build original request summary
            product_type = requirements.get("product_type", "")
            quantity = requirements.get("quantity", "")
            original_request = f"Request for {quantity} {product_type}" if product_type else "Your recent inquiry"
            
            # Determine rejection reason
            rejection_reason = state.get("feasibility_reason", "")
            if not rejection_reason:
                rejection_reason = state.get("approval_notes", "")
            if not rejection_reason:
                rejection_reason = "We are unable to fulfill your request at this time."
            
            # Get alternatives if available
            alternatives = state.get("alternatives", "")
            
            logger.info(
                f"Rejection for {lead_id}: reason='{rejection_reason[:100]}...', "
                f"has_alternatives={bool(alternatives)}"
            )
            
            # Generate rejection email
            email_result = write_rejection_email(
                customer_name=customer_name,
                customer_email=customer_email,
                original_request=original_request,
                rejection_reason=rejection_reason,
                alternatives=alternatives if alternatives else None,
            )
            
            subject = email_result.get(
                "subject",
                "Regarding Your Recent Request"
            )
            body = email_result.get("body", "")
            
            # Log the outgoing email
            log_outgoing_email(lead_id, customer_email, subject, body, "rejection")
            
            # Send the email
            send_result = send_email.invoke({
                "to_address": customer_email,
                "subject": subject,
                "body": body,
            })
            
            logger.info(f"Rejection email sent for lead {lead_id}: {send_result}")
            
            # Store in RAG storage
            storage = get_rag_storage()
            storage.store_lead_interaction(
                lead_id=lead_id,
                interaction_type="email_out",
                content=f"Subject: {subject}\n\n{body}",
                metadata={
                    "type": "rejection",
                    "reason": rejection_reason,
                },
            )
            
            result = {
                "status": FlowStatus.REJECTED,
                "outgoing_email_subject": subject,
                "outgoing_email_body": body,
                "current_node": "handle_rejection",
            }
            
            log_state_after("handle_rejection", state, result)
            return result
            
        except Exception as e:
            logger.error(f"Error handling rejection for {lead_id}: {e}")
            result = {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "handle_rejection",
            }
            log_state_after("handle_rejection", state, result)
            return result
