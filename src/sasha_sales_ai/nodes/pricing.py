"""Pricing calculation node"""

import json
import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..tools.pricing_tool import calculate_price
from ..chains.pricing_expert import generate_pricing_explanation, format_pricing_breakdown
from ..utils.langsmith_helpers import get_tracing_context
from ..utils.state_logger import log_state_before, log_state_after

logger = logging.getLogger("sasha_sales_ai.nodes.pricing")


def calculate_pricing(state: FlowState) -> dict[str, Any]:
    """Calculate pricing for the requested order.
    
    This node:
    1. Extracts product requirements from state
    2. Calculates pricing using the pricing tool
    3. Generates a customer-friendly explanation
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields with pricing information
    """
    lead_id = state.get("lead_id", "unknown")
    
    # Log state before execution
    log_state_before("calculate_pricing", state)
    
    with get_tracing_context(
        name="calculate_pricing",
        tags=["node", "pricing", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Calculating pricing for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            
            # Handle nested requirements structure (requirements.requirements.*)
            nested_req = requirements.get("requirements", {}) if isinstance(requirements.get("requirements"), dict) else {}
            
            # Extract product details - check both top-level and nested
            raw_product_type = requirements.get("product_type") or nested_req.get("product_type")
            product_type = raw_product_type if raw_product_type else "t-shirt"  # Default to t-shirt, not widget
            
            # Get quantity - check both top-level and nested
            quantity = requirements.get("quantity") or nested_req.get("quantity") or 0
            
            customizations = requirements.get("customizations") or nested_req.get("customizations")
            timeline = requirements.get("timeline") or nested_req.get("timeline")
            
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
                f"Pricing params: product={product_type}, qty={quantity}, "
                f"timeline={timeline_days}, custom={customizations}"
            )
            
            # Calculate price
            price_result_str = calculate_price.invoke({
                "product_type": product_type,
                "quantity": quantity,
                "customizations": customizations,
                "timeline_days": timeline_days,
            })
            
            price_data = json.loads(price_result_str)
            
            # Check for errors
            if "error" in price_data:
                logger.error(f"Pricing error for {lead_id}: {price_data['error']}")
                result = {
                    "status": FlowStatus.ERROR,
                    "error_message": price_data["error"],
                    "error_node": "calculate_pricing",
                }
                log_state_after("calculate_pricing", state, result)
                return result
            
            total_amount = price_data.get("grand_total", 0)
            
            # Format pricing breakdown
            pricing_breakdown = format_pricing_breakdown(price_data)
            
            logger.info(f"Pricing breakdown for {lead_id}:\n{pricing_breakdown}")
            
            # Generate explanation
            explanation_result = generate_pricing_explanation(
                product_type=product_type,
                quantity=quantity,
                customizations=customizations or "None",
                timeline_days=timeline_days or 14,
                pricing_breakdown=pricing_breakdown,
                total_amount=total_amount,
            )
            
            pricing_explanation = explanation_result.get(
                "explanation",
                pricing_breakdown
            )
            
            logger.info(f"Pricing calculated for {lead_id}: ${total_amount:,.2f}")
            
            result = {
                "price_quote": price_data,
                "pricing_explanation": pricing_explanation,
                "total_amount": total_amount,
                "status": FlowStatus.PRICING,
                "current_node": "calculate_pricing",
            }
            
            log_state_after("calculate_pricing", state, result)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating pricing for {lead_id}: {e}")
            result = {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "calculate_pricing",
            }
            log_state_after("calculate_pricing", state, result)
            return result
