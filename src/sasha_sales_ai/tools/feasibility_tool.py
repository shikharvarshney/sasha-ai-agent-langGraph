"""Feasibility check tool for validating order requirements."""

import json
import logging
from typing import Optional, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger("sasha_sales_ai.tools.feasibility")


# Business rules for feasibility checks
FEASIBILITY_RULES = {
    "min_quantity": 10,
    "max_quantity": 10000,
    "min_lead_time_days": 3,
    "max_lead_time_days": 90,
    "supported_products": [
        "t-shirt", "tshirt", "t shirt",
        "polo", "polo shirt",
        "hoodie", "hooded sweatshirt",
        "cap", "hat", "baseball cap",
        "mug", "coffee mug",
        "tote bag", "bag",
        "jacket",
    ],
    "supported_customizations": [
        "logo", "print", "printing", "printed",
        "embroidery", "embroidered",
        "screen print", "screen printed",
        "dtg", "direct to garment",
    ],
}


class FeasibilityResult(BaseModel):
    """Result of feasibility check."""
    is_feasible: bool
    reason: str
    alternatives: Optional[str] = None
    warnings: list[str] = []


def _format_result(result: FeasibilityResult) -> str:
    """Format the result as JSON string."""
    return json.dumps({
        "is_feasible": result.is_feasible,
        "reason": result.reason,
        "alternatives": result.alternatives,
        "warnings": result.warnings,
    })


@tool
def check_feasibility(
    product_type: Optional[str] = None,
    quantity: Optional[int] = None,
    timeline_days: Optional[int] = None,
    customizations: Optional[str] = None,
) -> str:
    """Check if a customer's order requirements are feasible based on business rules.
    
    This includes checking product availability, quantity limits, and timeline constraints.
    Returns feasibility status, reason, and any alternatives if not feasible.
    
    Args:
        product_type: Type of product requested (e.g., t-shirt, polo, hoodie)
        quantity: Quantity requested
        timeline_days: Requested delivery timeline in days
        customizations: Requested customizations (e.g., logo, embroidery)
    
    Returns:
        JSON string with feasibility result including is_feasible, reason, alternatives, and warnings
    """
    logger.info(f"Checking feasibility: product={product_type}, qty={quantity}, days={timeline_days}")
    
    warnings = []
    
    # Check product type
    if product_type:
        product_lower = product_type.lower()
        is_supported = any(
            supported in product_lower 
            for supported in FEASIBILITY_RULES["supported_products"]
        )
        if not is_supported:
            return _format_result(FeasibilityResult(
                is_feasible=False,
                reason=f"Product type '{product_type}' is not in our catalog.",
                alternatives="We offer: t-shirts, polos, hoodies, caps, mugs, tote bags, and jackets.",
            ))
    
    # Check quantity
    if quantity is not None:
        if quantity < FEASIBILITY_RULES["min_quantity"]:
            return _format_result(FeasibilityResult(
                is_feasible=False,
                reason=f"Minimum order quantity is {FEASIBILITY_RULES['min_quantity']} units.",
                alternatives=f"Please consider ordering at least {FEASIBILITY_RULES['min_quantity']} units.",
            ))
        elif quantity > FEASIBILITY_RULES["max_quantity"]:
            return _format_result(FeasibilityResult(
                is_feasible=False,
                reason=f"Maximum order quantity is {FEASIBILITY_RULES['max_quantity']} units per order.",
                alternatives="For larger orders, please contact our enterprise team.",
            ))
        
        # Warning for large orders
        if quantity > 1000:
            warnings.append("Large order - may require additional lead time.")
    
    # Check timeline
    if timeline_days is not None:
        if timeline_days < FEASIBILITY_RULES["min_lead_time_days"]:
            return _format_result(FeasibilityResult(
                is_feasible=False,
                reason=f"Minimum lead time is {FEASIBILITY_RULES['min_lead_time_days']} days.",
                alternatives=f"We can deliver in {FEASIBILITY_RULES['min_lead_time_days']} days with rush processing.",
            ))
        
        if timeline_days > FEASIBILITY_RULES["max_lead_time_days"]:
            warnings.append("Extended timeline - please confirm closer to desired date.")
    
    # Check customizations
    if customizations:
        custom_lower = customizations.lower()
        is_supported = any(
            supported in custom_lower
            for supported in FEASIBILITY_RULES["supported_customizations"]
        )
        if not is_supported:
            warnings.append(f"Customization '{customizations}' may require special handling.")
    
    # All checks passed
    logger.info(f"Feasibility check passed: product={product_type}, qty={quantity}")
    
    return _format_result(FeasibilityResult(
        is_feasible=True,
        reason="Order is feasible. All requirements are within our capabilities.",
        warnings=warnings,
    ))


@tool
def get_supported_products() -> str:
    """Get list of all supported products and customization options.
    
    Returns:
        JSON string with supported products and customizations
    """
    return json.dumps({
        "supported_products": [
            "t-shirt", "polo", "hoodie", "cap", "mug", "tote bag", "jacket"
        ],
        "supported_customizations": [
            "logo printing", "embroidery", "screen print", "DTG (direct to garment)"
        ],
        "quantity_limits": {
            "min": FEASIBILITY_RULES["min_quantity"],
            "max": FEASIBILITY_RULES["max_quantity"],
        },
        "timeline_limits": {
            "min_days": FEASIBILITY_RULES["min_lead_time_days"],
            "max_days": FEASIBILITY_RULES["max_lead_time_days"],
        },
    })


@tool
def check_timeline_feasibility(
    quantity: int,
    requested_days: int,
) -> str:
    """Check if a specific timeline is feasible for a given quantity.
    
    Args:
        quantity: Number of units to produce
        requested_days: Requested delivery timeline in days
    
    Returns:
        JSON string with timeline feasibility and recommendations
    """
    logger.info(f"Checking timeline feasibility: qty={quantity}, days={requested_days}")
    
    # Base minimum days
    min_days = FEASIBILITY_RULES["min_lead_time_days"]
    
    # Add extra days for larger quantities
    if quantity > 500:
        min_days += 2
    if quantity > 1000:
        min_days += 3
    if quantity > 5000:
        min_days += 5
    
    is_feasible = requested_days >= min_days
    
    result = {
        "is_feasible": is_feasible,
        "requested_days": requested_days,
        "minimum_days_required": min_days,
        "recommendation": None,
    }
    
    if not is_feasible:
        result["recommendation"] = f"For {quantity} units, we need at least {min_days} days. Consider rush processing for faster delivery (additional charges apply)."
    else:
        buffer_days = requested_days - min_days
        if buffer_days >= 7:
            result["recommendation"] = "Timeline is comfortable. Standard processing recommended."
        elif buffer_days >= 3:
            result["recommendation"] = "Timeline is tight but achievable with priority processing."
        else:
            result["recommendation"] = "Timeline is very tight. Rush processing strongly recommended."
    
    return json.dumps(result)
