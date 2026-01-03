"""Order confirmation node"""

import logging
from typing import Any
from datetime import datetime, timedelta

from ..state import FlowState, FlowStatus
from ..chains.email_writer import write_confirmation_email
from ..tools.email_tool import send_email
from ..tools.order_tool import format_order_details
from ..storage.rag_storage import get_rag_storage
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.confirmation")


def send_confirmation(state: FlowState) -> dict[str, Any]:
    """Send order confirmation to the customer.
    
    This node:
    1. Generates a professional confirmation email
    2. Sends it to the customer
    3. Stores the interaction
    4. Marks the flow as completed
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="send_confirmation",
        tags=["node", "confirmation", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Sending confirmation for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            price_quote = state.get("price_quote", {})
            total_amount = state.get("total_amount", 0)
            order_id = state.get("order_id", "")
            
            customer_name = requirements.get("customer_name", "")
            customer_email = state.get("email_from", "")
            product_type = requirements.get("product_type", "widget")
            quantity = requirements.get("quantity", 0)
            
            # Parse quantity
            if isinstance(quantity, str):
                try:
                    quantity = int(quantity.replace(",", ""))
                except ValueError:
                    quantity = 0
            
            # Calculate estimated delivery
            timeline = requirements.get("timeline")
            if timeline:
                if isinstance(timeline, str):
                    import re
                    numbers = re.findall(r'\d+', timeline)
                    if numbers:
                        days = int(numbers[0])
                        if "week" in timeline.lower():
                            days *= 7
                        elif "month" in timeline.lower():
                            days *= 30
                    else:
                        days = 14
                else:
                    days = int(timeline)
            else:
                days = 14
            
            estimated_delivery = (datetime.now() + timedelta(days=days)).strftime("%B %d, %Y")
            
            # Format order details
            order_details = format_order_details({
                "product_type": product_type,
                "quantity": quantity,
                "customizations": requirements.get("customizations"),
                "total_amount": total_amount,
            })
            
            # Generate confirmation email
            email_result = write_confirmation_email(
                customer_name=customer_name,
                customer_email=customer_email,
                order_id=order_id,
                product_type=product_type,
                quantity=quantity,
                total_amount=total_amount,
                estimated_delivery=estimated_delivery,
                additional_details=order_details,
            )
            
            subject = email_result.get(
                "subject",
                f"Order Confirmation - #{order_id}"
            )
            body = email_result.get("body", "")
            
            # Send the email
            send_result = send_email.invoke({
                "to_address": customer_email,
                "subject": subject,
                "body": body,
            })
            
            logger.info(f"Confirmation email sent for lead {lead_id}: {send_result}")
            
            # Store in RAG storage
            storage = get_rag_storage()
            storage.store_lead_interaction(
                lead_id=lead_id,
                interaction_type="email_out",
                content=f"Subject: {subject}\n\n{body}",
                metadata={
                    "type": "confirmation",
                    "order_id": order_id,
                },
            )
            
            return {
                "status": FlowStatus.COMPLETED,
                "outgoing_email_subject": subject,
                "outgoing_email_body": body,
                "current_node": "send_confirmation",
            }
            
        except Exception as e:
            logger.error(f"Error sending confirmation for {lead_id}: {e}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "send_confirmation",
            }

