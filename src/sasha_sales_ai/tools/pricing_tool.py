"""Pricing calculation tool"""

import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("sasha_sales_ai.tools.pricing")

# Base pricing structure
BASE_PRICES = {
    "widget": 5.00,
    "gadget": 15.00,
    "component": 2.50,
    "assembly": 75.00,
}

# Volume discount tiers (quantity threshold, discount percentage)
VOLUME_DISCOUNTS = [
    (1000, 0.15),   # 15% off for 1000+
    (500, 0.10),    # 10% off for 500+
    (100, 0.05),    # 5% off for 100+
]

# Customization pricing
CUSTOMIZATION_PRICES = {
    "logo_printing": 0.50,      # per unit
    "color_matching": 0.25,     # per unit
    "special_packaging": 1.00,  # per unit
    "engraving": 2.00,          # per unit
    "custom_shape": 5.00,       # per unit
}

# Rush order multipliers (days, multiplier)
RUSH_MULTIPLIERS = [
    (3, 1.50),   # 50% surcharge for 3 days or less
    (5, 1.25),   # 25% surcharge for 5 days or less
    (7, 1.10),   # 10% surcharge for 7 days or less
]


@tool
def calculate_price(
    product_type: str,
    quantity: int,
    customizations: Optional[str] = None,
    timeline_days: Optional[int] = None,
) -> str:
    """Calculate the total price for an order with detailed breakdown.
    
    Args:
        product_type: Type of product (widget, gadget, component, assembly)
        quantity: Number of units
        customizations: Comma-separated list of customizations
        timeline_days: Delivery timeline in days (for rush pricing)
    
    Returns:
        JSON string with price breakdown and total
    """
    import json
    
    logger.info(f"Calculating price: {product_type} x {quantity}")
    
    product_type_lower = product_type.lower().strip()
    
    # Check product exists
    if product_type_lower not in BASE_PRICES:
        return json.dumps({
            "error": f"Unknown product type: {product_type}",
            "available_products": list(BASE_PRICES.keys()),
        })
    
    # Base price calculation
    base_price = BASE_PRICES[product_type_lower]
    subtotal = base_price * quantity
    
    breakdown = {
        "product_type": product_type_lower,
        "quantity": quantity,
        "base_price_per_unit": base_price,
        "base_subtotal": subtotal,
        "line_items": [
            {
                "description": f"{product_type_lower.title()} x {quantity}",
                "unit_price": base_price,
                "quantity": quantity,
                "total": subtotal,
            }
        ],
        "discounts": [],
        "surcharges": [],
    }
    
    # Apply volume discount
    volume_discount = 0
    for threshold, discount_rate in VOLUME_DISCOUNTS:
        if quantity >= threshold:
            volume_discount = subtotal * discount_rate
            breakdown["discounts"].append({
                "description": f"Volume discount ({int(discount_rate * 100)}% for {threshold}+ units)",
                "amount": -volume_discount,
            })
            break
    
    # Calculate customization costs
    customization_total = 0
    if customizations:
        custom_list = [c.strip().lower().replace(" ", "_") for c in customizations.split(",")]
        for custom in custom_list:
            if custom in CUSTOMIZATION_PRICES:
                custom_cost = CUSTOMIZATION_PRICES[custom] * quantity
                customization_total += custom_cost
                breakdown["line_items"].append({
                    "description": f"Customization: {custom.replace('_', ' ').title()}",
                    "unit_price": CUSTOMIZATION_PRICES[custom],
                    "quantity": quantity,
                    "total": custom_cost,
                })
    
    # Calculate rush surcharge
    rush_surcharge = 0
    if timeline_days is not None:
        for days_threshold, multiplier in RUSH_MULTIPLIERS:
            if timeline_days <= days_threshold:
                # Apply multiplier to base subtotal only
                rush_surcharge = subtotal * (multiplier - 1)
                breakdown["surcharges"].append({
                    "description": f"Rush delivery ({timeline_days} days)",
                    "multiplier": multiplier,
                    "amount": rush_surcharge,
                })
                break
    
    # Calculate totals
    subtotal_after_discount = subtotal - volume_discount
    total_before_surcharge = subtotal_after_discount + customization_total
    grand_total = total_before_surcharge + rush_surcharge
    
    breakdown["subtotal_after_discount"] = subtotal_after_discount
    breakdown["customization_total"] = customization_total
    breakdown["rush_surcharge"] = rush_surcharge
    breakdown["grand_total"] = round(grand_total, 2)
    
    logger.info(f"Calculated price: ${grand_total:.2f}")
    
    return json.dumps(breakdown)


@tool
def get_pricing_tiers() -> str:
    """Get information about pricing tiers and discounts.
    
    Returns:
        JSON string with pricing information
    """
    import json
    
    return json.dumps({
        "base_prices": BASE_PRICES,
        "volume_discounts": [
            {"min_quantity": qty, "discount_percent": int(disc * 100)}
            for qty, disc in VOLUME_DISCOUNTS
        ],
        "customizations": {
            k: {"price_per_unit": v}
            for k, v in CUSTOMIZATION_PRICES.items()
        },
        "rush_delivery": [
            {"max_days": days, "surcharge_percent": int((mult - 1) * 100)}
            for days, mult in RUSH_MULTIPLIERS
        ],
    })


@tool
def estimate_quick_price(product_type: str, quantity: int) -> str:
    """Get a quick price estimate without customizations or rush pricing.
    
    Args:
        product_type: Type of product
        quantity: Number of units
    
    Returns:
        Quick price estimate string
    """
    product_type_lower = product_type.lower().strip()
    
    if product_type_lower not in BASE_PRICES:
        return f"Unknown product type: {product_type}"
    
    base = BASE_PRICES[product_type_lower] * quantity
    
    # Apply volume discount
    for threshold, discount_rate in VOLUME_DISCOUNTS:
        if quantity >= threshold:
            base *= (1 - discount_rate)
            break
    
    return f"Estimated price for {quantity} {product_type}(s): ${base:,.2f}"

