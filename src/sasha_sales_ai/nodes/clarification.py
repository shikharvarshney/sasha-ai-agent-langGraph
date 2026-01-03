"""Clarification request node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..chains.email_writer import write_clarification_email
from ..tools.email_tool import send_email
from ..storage.rag_storage import get_rag_storage
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.clarification")


def request_clarification(state: FlowState) -> dict[str, Any]:
    """Request additional information from the customer.
    
    This node:
    1. Generates a clarification email using the email writer chain
    2. Sends the email to the customer
    3. Stores the interaction in RAG storage
    4. Updates status to wait for reply
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="request_clarification",
        tags=["node", "clarification", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Requesting clarification for lead {lead_id}")
        
        try:
            # Extract customer info from requirements
            requirements = state.get("requirements", {})
            customer_name = requirements.get("customer_name", "")
            customer_email = state.get("email_from", "")
            missing_fields = state.get("missing_fields", [])
            
            # Create request summary from original email
            request_summary = requirements.get(
                "summary",
                f"Your inquiry about {state.get('email_subject', 'our products')}"
            )
            
            # Generate clarification email
            email_result = write_clarification_email(
                customer_name=customer_name,
                customer_email=customer_email,
                request_summary=request_summary,
                missing_info=missing_fields,
            )
            
            subject = email_result.get("subject", "Additional Information Needed")
            body = email_result.get("body", "")
            
            # Send the email
            send_result = send_email.invoke({
                "to_address": customer_email,
                "subject": subject,
                "body": body,
            })
            
            logger.info(f"Clarification email sent for lead {lead_id}: {send_result}")
            
            # Store in RAG storage
            storage = get_rag_storage()
            storage.store_lead_interaction(
                lead_id=lead_id,
                interaction_type="email_out",
                content=f"Subject: {subject}\n\n{body}",
                metadata={"type": "clarification"},
            )
            
            return {
                "status": FlowStatus.CLARIFYING,
                "outgoing_email_subject": subject,
                "outgoing_email_body": body,
                "current_node": "request_clarification",
            }
            
        except Exception as e:
            logger.error(f"Error requesting clarification for {lead_id}: {e}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "request_clarification",
            }

