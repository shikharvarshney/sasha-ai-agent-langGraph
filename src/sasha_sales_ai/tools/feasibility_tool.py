"""Feasibility checking tool"""

import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("sasha_sales_ai.tools.feasibility")

# Product catalog with capabilities
PRODUCT_CATALOG = {
    "widget": {
        "min_quantity": 10,
        "max_quantity": 10000,
        "min_timeline_days": 3,
        "customization_available": True,
        "materials": ["plastic", "metal", "wood"],
    },
    "gadget": {
        "min_quantity": 5,
        "max_quantity": 5000,
        "min_timeline_days": 5,
        "customization_available": True,
        "materials": ["plastic", "metal"],
    },
    "component": {
        "min_quantity": 100,
        "max_quantity": 50000,
        "min_timeline_days": 7,
        "customization_available": False,
        "materials": ["metal", "composite"],
    },
    "assembly": {
        "min_quantity": 1,
        "max_quantity": 1000,
        "min_timeline_days": 14,
        "customization_available": True,
        "materials": ["mixed"],
    },
}


@tool
def check_product_feasibility(
    product_type: str,
    quantity: int,
    timeline_days: Optional[int] = None,
    customizations: Optional[str] = None,
    material: Optional[str] = None,
) -> str:
    """Check if a product order is feasible given the requirements.
    
    Args:
        product_type: Type of product (widget, gadget, component, assembly)
        quantity: Number of units requested
        timeline_days: Optional requested delivery timeline in days
        customizations: Optional customization requirements
        material: Optional material specification
    
    Returns:
        JSON string with feasibility result, reason, and any alternatives
    """
    import json
    
    logger.info(f"Checking feasibility: {product_type} x {quantity}")
    
    result = {
        "is_feasible": False,
        "reason": "",
        "alternatives": "",
    }
    
    # Normalize product type
    product_type_lower = product_type.lower().strip()
    
    # Check if product exists
    if product_type_lower not in PRODUCT_CATALOG:
        result["reason"] = f"Product type '{product_type}' is not in our catalog."
        result["alternatives"] = f"Available products: {', '.join(PRODUCT_CATALOG.keys())}"
        return json.dumps(result)
    
    product = PRODUCT_CATALOG[product_type_lower]
    
    # Check quantity limits
    if quantity < product["min_quantity"]:
        result["reason"] = f"Minimum order quantity for {product_type} is {product['min_quantity']} units."
        result["alternatives"] = f"Consider ordering at least {product['min_quantity']} units."
        return json.dumps(result)
    
    if quantity > product["max_quantity"]:
        result["reason"] = f"Maximum order quantity for {product_type} is {product['max_quantity']} units per order."
        result["alternatives"] = f"Consider splitting into multiple orders of {product['max_quantity']} units each."
        return json.dumps(result)
    
    # Check timeline
    if timeline_days is not None and timeline_days < product["min_timeline_days"]:
        result["reason"] = f"Minimum production time for {product_type} is {product['min_timeline_days']} days."
        result["alternatives"] = f"We can deliver in {product['min_timeline_days']} days with rush processing (additional charges may apply)."
        return json.dumps(result)
    
    # Check customization
    if customizations and not product["customization_available"]:
        result["reason"] = f"Customization is not available for {product_type}."
        result["alternatives"] = "Consider our 'widget' or 'gadget' products which support customization."
        return json.dumps(result)
    
    # Check material
    if material:
        material_lower = material.lower().strip()
        if material_lower not in product["materials"] and "mixed" not in product["materials"]:
            result["reason"] = f"Material '{material}' is not available for {product_type}."
            result["alternatives"] = f"Available materials: {', '.join(product['materials'])}"
            return json.dumps(result)
    
    # All checks passed
    result["is_feasible"] = True
    result["reason"] = "Order is feasible and can be processed."
    
    logger.info(f"Feasibility check passed for {product_type} x {quantity}")
    
    return json.dumps(result)


@tool
def get_product_specifications(product_type: str) -> str:
    """Get detailed specifications for a product type.
    
    Args:
        product_type: Type of product to get specifications for
    
    Returns:
        JSON string with product specifications
    """
    import json
    
    product_type_lower = product_type.lower().strip()
    
    if product_type_lower not in PRODUCT_CATALOG:
        return json.dumps({
            "error": f"Product type '{product_type}' not found",
            "available_products": list(PRODUCT_CATALOG.keys()),
        })
    
    specs = PRODUCT_CATALOG[product_type_lower].copy()
    specs["product_type"] = product_type_lower
    
    return json.dumps(specs)


@tool
def list_available_products() -> str:
    """List all available products and their basic specifications.
    
    Returns:
        JSON string with all product types and basic info
    """
    import json
    
    products = []
    for name, specs in PRODUCT_CATALOG.items():
        products.append({
            "name": name,
            "quantity_range": f"{specs['min_quantity']} - {specs['max_quantity']}",
            "min_timeline_days": specs["min_timeline_days"],
            "customization_available": specs["customization_available"],
        })
    
    return json.dumps({"products": products})

