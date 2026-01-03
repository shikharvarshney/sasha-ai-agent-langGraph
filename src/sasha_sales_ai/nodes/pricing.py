"""Pricing calculation node"""

import json
import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..tools.pricing_tool import calculate_price
from ..chains.pricing_expert import generate_pricing_explanation, format_pricing_breakdown
from ..utils.langsmith_helpers import get_tracing_context

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
    
    with get_tracing_context(
        name="calculate_pricing",
        tags=["node", "pricing", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Calculating pricing for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            
            # Extract product details
            product_type = requirements.get("product_type", "widget")
            quantity = requirements.get("quantity", 0)
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
                return {
                    "status": FlowStatus.ERROR,
                    "error_message": price_data["error"],
                    "error_node": "calculate_pricing",
                }
            
            total_amount = price_data.get("grand_total", 0)
            
            # Format pricing breakdown
            pricing_breakdown = format_pricing_breakdown(price_data)
            
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
            
            return {
                "price_quote": price_data,
                "pricing_explanation": pricing_explanation,
                "total_amount": total_amount,
                "status": FlowStatus.PRICING,
                "current_node": "calculate_pricing",
            }
            
        except Exception as e:
            logger.error(f"Error calculating pricing for {lead_id}: {e}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "calculate_pricing",
            }

