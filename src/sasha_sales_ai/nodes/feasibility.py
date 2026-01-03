"""Feasibility check node"""

import json
import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..tools.feasibility_tool import check_product_feasibility
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.feasibility")


def check_feasibility(state: FlowState) -> dict[str, Any]:
    """Check if the requested order is feasible.
    
    This node:
    1. Extracts product requirements from state
    2. Runs feasibility check against product catalog
    3. Captures alternatives if not feasible
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="check_feasibility",
        tags=["node", "feasibility", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Checking feasibility for lead {lead_id}")
        
        try:
            requirements = state.get("requirements", {})
            
            # Extract product details
            product_type = requirements.get("product_type", "widget")
            quantity = requirements.get("quantity", 0)
            timeline = requirements.get("timeline")
            customizations = requirements.get("customizations")
            material = requirements.get("material")
            
            # Parse quantity if it's a string
            if isinstance(quantity, str):
                try:
                    quantity = int(quantity.replace(",", ""))
                except ValueError:
                    quantity = 0
            
            # Parse timeline if provided
            timeline_days = None
            if timeline:
                # Try to extract days from timeline string
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
            
            # Run feasibility check
            result_str = check_product_feasibility.invoke({
                "product_type": product_type,
                "quantity": quantity,
                "timeline_days": timeline_days,
                "customizations": customizations,
                "material": material,
            })
            
            result = json.loads(result_str)
            
            is_feasible = result.get("is_feasible", False)
            reason = result.get("reason", "")
            alternatives = result.get("alternatives", "")
            
            logger.info(f"Feasibility for {lead_id}: {is_feasible} - {reason}")
            
            return {
                "is_feasible": is_feasible,
                "feasibility_reason": reason,
                "alternatives": alternatives,
                "feasibility_checked": True,
                "status": FlowStatus.FEASIBILITY,
                "current_node": "check_feasibility",
            }
            
        except Exception as e:
            logger.error(f"Error checking feasibility for {lead_id}: {e}")
            return {
                "is_feasible": False,
                "feasibility_reason": f"Error during feasibility check: {str(e)}",
                "alternatives": "",
                "feasibility_checked": True,
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "check_feasibility",
            }

