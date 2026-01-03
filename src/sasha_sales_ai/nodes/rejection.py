"""Rejection handling node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..chains.email_writer import write_rejection_email
from ..tools.email_tool import send_email
from ..storage.rag_storage import get_rag_storage
from ..utils.langsmith_helpers import get_tracing_context

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
            
            # Determine rejection reason
            rejection_reason = state.get("feasibility_reason", "")
            if not rejection_reason:
                rejection_reason = state.get("approval_notes", "")
            if not rejection_reason:
                rejection_reason = "We are unable to fulfill your request at this time."
            
            # Get alternatives if available
            alternatives = state.get("alternatives", "")
            
            # Generate rejection email
            email_result = write_rejection_email(
                customer_name=customer_name,
                customer_email=customer_email,
                rejection_reason=rejection_reason,
                alternatives=alternatives if alternatives else None,
            )
            
            subject = email_result.get(
                "subject",
                "Regarding Your Recent Request"
            )
            body = email_result.get("body", "")
            
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
            
            return {
                "status": FlowStatus.REJECTED,
                "outgoing_email_subject": subject,
                "outgoing_email_body": body,
                "current_node": "handle_rejection",
            }
            
        except Exception as e:
            logger.error(f"Error handling rejection for {lead_id}: {e}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "handle_rejection",
            }

