"""Order placement node"""

import json
import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..tools.order_tool import create_order
from ..utils.langsmith_helpers import get_tracing_context
from ..utils.state_logger import log_state_before, log_state_after

logger = logging.getLogger("sasha_sales_ai.nodes.order")


def place_order(state: FlowState) -> dict[str, Any]:
    """Place an order after customer confirmation.
    
    This node:
    1. Creates the order in the system
    2. Captures order ID and details
    3. Updates status to order placed
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields with order information
    """
    lead_id = state.get("lead_id", "unknown")
    
    # Log state before execution
    log_state_before("place_order", state)
    
    with get_tracing_context(
        name="place_order",
        tags=["node", "order", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Placing order for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            price_quote = state.get("price_quote", {})
            total_amount = state.get("total_amount", 0)
            feasibility_checked = state.get("feasibility_checked", False)
            quote_sent = state.get("quote_sent", False)
            missing_fields = state.get("missing_fields", [])
            
            # Handle nested requirements structure (requirements.requirements.*)
            nested_req = requirements.get("requirements", {}) if isinstance(requirements.get("requirements"), dict) else {}
            
            customer_email = state.get("email_from", "")
            raw_product_type = requirements.get("product_type") or nested_req.get("product_type")
            product_type = raw_product_type if raw_product_type else "t-shirt"  # Default to t-shirt, not widget
            
            # Get quantity - check both top-level and nested
            quantity = requirements.get("quantity") or nested_req.get("quantity") or 0
            
            customizations = requirements.get("customizations")
            timeline = requirements.get("timeline")
            
            # Parse quantity
            if isinstance(quantity, str):
                try:
                    quantity = int(quantity.replace(",", ""))
                except ValueError:
                    quantity = 0
            
            # Parse timeline to days
            timeline_days = None
            if timeline:
                if isinstance(timeline, str):
                    import re
                    numbers = re.findall(r'\d+', timeline)
                    if numbers:
                        timeline_days = int(numbers[0])
                        if "week" in timeline.lower():
                            timeline_days *= 7
                        elif "month" in timeline.lower():
                            timeline_days *= 30
                else:
                    timeline_days = int(timeline)
            
            logger.info(
                f"Creating order: product={product_type}, qty={quantity}, "
                f"total=${total_amount:,.2f}, customer={customer_email}"
            )
            
            # Create the order
            order_result_str = create_order.invoke({
                "lead_id": lead_id,
                "customer_email": customer_email,
                "product_type": product_type,
                "quantity": quantity,
                "total_amount": total_amount,
                "customizations": customizations,
                "timeline_days": timeline_days,
                "notes": f"From lead {lead_id}",
            })
            
            order_data = json.loads(order_result_str)
            
            if "error" in order_data:
                logger.error(f"Order creation error for {lead_id}: {order_data['error']}")
                result = {
                    "status": FlowStatus.ERROR,
                    "error_message": order_data["error"],
                    "error_node": "place_order",
                }
                log_state_after("place_order", state, result)
                return result
            
            order_id = order_data.get("order_id", "")
            
            logger.info(f"Order placed for {lead_id}: {order_id}")
            
            result = {
                "order_id": order_id,
                "status": FlowStatus.ORDER_PLACED,
                "current_node": "place_order",
            }
            
            log_state_after("place_order", state, result)
            return result
            
        except Exception as e:
            logger.error(f"Error placing order for {lead_id}: {e}")
            result = {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "place_order",
            }
            log_state_after("place_order", state, result)
            return result
