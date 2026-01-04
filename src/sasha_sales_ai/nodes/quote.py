"""Quote sending node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..chains.email_writer import write_quote_email
from ..chains.pricing_expert import format_pricing_breakdown
from ..tools.email_tool import send_email
from ..storage.rag_storage import get_rag_storage
from ..utils.langsmith_helpers import get_tracing_context
from ..utils.state_logger import log_state_before, log_state_after, log_outgoing_email

logger = logging.getLogger("sasha_sales_ai.nodes.quote")


def send_quote(state: FlowState) -> dict[str, Any]:
    """Send a price quote to the customer.
    
    This node:
    1. Generates a professional quote email
    2. Sends it to the customer
    3. Stores the interaction in RAG storage
    4. Marks quote as sent (interrupt point - waiting for reply)
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    # Log state before execution
    log_state_before("send_quote", state)
    
    with get_tracing_context(
        name="send_quote",
        tags=["node", "quote", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Sending quote for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            price_quote = state.get("price_quote", {})
            total_amount = state.get("total_amount", 0)
            
            # Handle nested requirements structure
            nested_req = requirements.get("requirements", {}) if isinstance(requirements.get("requirements"), dict) else {}
            
            customer_name = requirements.get("customer_name") or nested_req.get("customer_name") or ""
            customer_email = state.get("email_from", "")
            
            # Build order summary - check both top-level and nested
            product_type = requirements.get("product_type") or nested_req.get("product_type") or "product"
            quantity = requirements.get("quantity") or nested_req.get("quantity") or 0
            customizations = requirements.get("customizations") or nested_req.get("customizations") or ""
            
            order_summary = f"{quantity} x {product_type}"
            if customizations:
                order_summary += f" with {customizations}"
            
            # Format quote details
            quote_details = format_pricing_breakdown(price_quote)
            
            # Get pricing explanation for additional context
            pricing_breakdown = state.get("pricing_explanation", quote_details)
            
            # Generate quote email
            email_result = write_quote_email(
                customer_name=customer_name,
                customer_email=customer_email,
                order_summary=order_summary,
                quote_details=quote_details,
                total_amount=total_amount,
                pricing_breakdown=pricing_breakdown,
            )
            
            subject = email_result.get(
                "subject",
                f"Your Quote Request - ${total_amount:,.2f}"
            )
            body = email_result.get("body", "")
            
            # Log the outgoing email
            log_outgoing_email(lead_id, customer_email, subject, body, "quote")
            
            # Send the email
            send_result = send_email.invoke({
                "to_address": customer_email,
                "subject": subject,
                "body": body,
            })
            
            logger.info(f"Quote email sent for lead {lead_id}: {send_result}")
            
            # Store in RAG storage
            storage = get_rag_storage()
            storage.store_lead_interaction(
                lead_id=lead_id,
                interaction_type="email_out",
                content=f"Subject: {subject}\n\n{body}",
                metadata={
                    "type": "quote",
                    "total_amount": total_amount,
                },
            )
            
            result = {
                "status": FlowStatus.QUOTE_SENT,
                "quote_sent": True,
                "outgoing_email_subject": subject,
                "outgoing_email_body": body,
                "current_node": "send_quote",
            }
            
            log_state_after("send_quote", state, result)
            return result
            
        except Exception as e:
            logger.error(f"Error sending quote for {lead_id}: {e}")
            result = {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "send_quote",
            }
            log_state_after("send_quote", state, result)
            return result
