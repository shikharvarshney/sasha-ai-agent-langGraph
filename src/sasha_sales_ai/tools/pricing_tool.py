"""Pricing calculation tool for promotional products."""

import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("sasha_sales_ai.tools.pricing")

# Pricing rules and rates for promotional products
PRICING_RULES = {
    "base_prices": {
        "t-shirt": 10.00,
        "tshirt": 10.00,
        "polo": 15.00,
        "hoodie": 25.00,
        "cap": 8.00,
        "hat": 8.00,
        "mug": 12.00,
        "tote bag": 7.00,
        "tote_bag": 7.00,
        "bag": 7.00,
        "jacket": 40.00,
    },
    "customization_prices": {
        "logo": 2.00,           # per item
        "logo_print": 2.00,
        "print": 2.00,
        "printing": 2.00,
        "embroidery": 4.00,
        "embroidered": 4.00,
        "screen print": 1.50,
        "screen_print": 1.50,
        "dtg": 3.00,
        "direct to garment": 3.00,
    },
    "setup_fees": {
        "logo": 25.00,
        "logo_print": 25.00,
        "print": 25.00,
        "printing": 25.00,
        "embroidery": 50.00,
        "embroidered": 50.00,
        "screen print": 35.00,
        "screen_print": 35.00,
        "dtg": 0.00,
        "direct to garment": 0.00,
    },
    "quantity_discounts": {
        100: 0.05,    # 5% off for 100+
        500: 0.10,    # 10% off for 500+
        1000: 0.15,   # 15% off for 1000+
    },
    "rush_fee_percent": 0.25,  # 25% extra for rush orders (< 7 days)
    "shipping_base": 15.00,
    "shipping_per_item": 0.50,
    "max_shipping": 250.00,
}


@tool
def calculate_price(
    product_type: str,
    quantity: int,
    customizations: Optional[str] = None,
    timeline_days: Optional[int] = None,
) -> str:
    """Calculate the total price for an order with detailed breakdown.
    
    Args:
        product_type: Type of product (t-shirt, polo, hoodie, cap, mug, tote bag, jacket)
        quantity: Number of units
        customizations: Type of customization (logo, embroidery, screen print, dtg)
        timeline_days: Delivery timeline in days (for rush pricing)
    
    Returns:
        JSON string with price breakdown and total
    """
    import json
    
    logger.info(f"Calculating price: {product_type} x {quantity}, custom={customizations}, timeline={timeline_days}")
    
    product_type_lower = product_type.lower().strip()
    
    # Find base price (handle variations)
    base_price = None
    matched_product = None
    for key, price in PRICING_RULES["base_prices"].items():
        if key in product_type_lower or product_type_lower in key:
            base_price = price
            matched_product = key
            break
    
    if base_price is None:
        return json.dumps({
            "error": f"Unknown product type: {product_type}",
            "available_products": ["t-shirt", "polo", "hoodie", "cap", "mug", "tote bag", "jacket"],
        })
    
    # Base price calculation
    subtotal = base_price * quantity
    
    breakdown = {
        "product_type": matched_product,
        "quantity": quantity,
        "base_price_per_unit": base_price,
        "base_subtotal": subtotal,
        "line_items": [
            {
                "description": f"{matched_product.replace('_', ' ').title()} x {quantity}",
                "unit_price": base_price,
                "quantity": quantity,
                "total": subtotal,
            }
        ],
        "discounts": [],
        "surcharges": [],
    }
    
    # Calculate customization costs
    customization_total = 0
    setup_fee = 0
    if customizations:
        custom_lower = customizations.lower()
        
        # Find matching customization type
        for key, price in PRICING_RULES["customization_prices"].items():
            if key in custom_lower:
                customization_total = price * quantity
                setup_fee = PRICING_RULES["setup_fees"].get(key, 0)
                
                breakdown["line_items"].append({
                    "description": f"Customization: {key.replace('_', ' ').title()}",
                    "unit_price": price,
                    "quantity": quantity,
                    "total": customization_total,
                })
                
                if setup_fee > 0:
                    breakdown["line_items"].append({
                        "description": f"Setup Fee ({key.replace('_', ' ').title()})",
                        "unit_price": setup_fee,
                        "quantity": 1,
                        "total": setup_fee,
                    })
                
                breakdown["customization_type"] = key
                breakdown["customization_per_item"] = price
                break
    
    # Calculate quantity discount
    volume_discount = 0
    discount_percent = 0
    for threshold, discount_rate in sorted(PRICING_RULES["quantity_discounts"].items(), reverse=True):
        if quantity >= threshold:
            discount_percent = discount_rate
            volume_discount = (subtotal + customization_total) * discount_rate
            breakdown["discounts"].append({
                "description": f"Volume discount ({int(discount_rate * 100)}% for {threshold}+ units)",
                "amount": volume_discount,
            })
            break
    
    breakdown["discount_percent"] = discount_percent * 100
    breakdown["discount_amount"] = volume_discount
    
    # Calculate rush surcharge
    rush_surcharge = 0
    if timeline_days is not None and timeline_days < 7:
        rush_surcharge = subtotal * PRICING_RULES["rush_fee_percent"]
        breakdown["surcharges"].append({
            "description": f"Rush delivery ({timeline_days} days)",
            "percent": PRICING_RULES["rush_fee_percent"] * 100,
            "amount": rush_surcharge,
        })
        breakdown["rush_fee"] = rush_surcharge
        breakdown["rush_fee_note"] = f"Rush delivery ({timeline_days} days)"
    
    # Calculate shipping
    shipping = PRICING_RULES["shipping_base"] + (PRICING_RULES["shipping_per_item"] * quantity)
    shipping = min(shipping, PRICING_RULES["max_shipping"])
    breakdown["shipping"] = shipping
    
    # Calculate totals
    subtotal_after_discount = subtotal + customization_total + setup_fee - volume_discount
    grand_total = subtotal_after_discount + rush_surcharge + shipping
    
    breakdown["subtotal_after_discount"] = round(subtotal_after_discount, 2)
    breakdown["customization_total"] = customization_total
    breakdown["setup_fee"] = setup_fee
    breakdown["rush_surcharge"] = rush_surcharge
    breakdown["grand_total"] = round(grand_total, 2)
    
    logger.info(f"Calculated price: ${grand_total:.2f}")
    
    return json.dumps(breakdown)


@tool
def get_pricing_tiers() -> str:
    """Get information about pricing tiers, discounts, and customization options.
    
    Returns:
        JSON string with pricing information
    """
    import json
    
    # Dedupe base prices for display
    unique_products = {
        "t-shirt": 10.00,
        "polo": 15.00,
        "hoodie": 25.00,
        "cap": 8.00,
        "mug": 12.00,
        "tote_bag": 7.00,
        "jacket": 40.00,
    }
    
    unique_customizations = {
        "logo_print": {"per_item": 2.00, "setup_fee": 25.00},
        "embroidery": {"per_item": 4.00, "setup_fee": 50.00},
        "screen_print": {"per_item": 1.50, "setup_fee": 35.00},
        "dtg": {"per_item": 3.00, "setup_fee": 0.00},
    }
    
    return json.dumps({
        "base_prices": unique_products,
        "volume_discounts": [
            {"min_quantity": qty, "discount_percent": int(disc * 100)}
            for qty, disc in sorted(PRICING_RULES["quantity_discounts"].items())
        ],
        "customizations": unique_customizations,
        "rush_delivery": {
            "applies_when": "timeline < 7 days",
            "surcharge_percent": int(PRICING_RULES["rush_fee_percent"] * 100),
        },
        "shipping": {
            "base": PRICING_RULES["shipping_base"],
            "per_item": PRICING_RULES["shipping_per_item"],
            "max": PRICING_RULES["max_shipping"],
        },
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
    
    # Find base price
    base_price = None
    for key, price in PRICING_RULES["base_prices"].items():
        if key in product_type_lower or product_type_lower in key:
            base_price = price
            break
    
    if base_price is None:
        return f"Unknown product type: {product_type}. Available: t-shirt, polo, hoodie, cap, mug, tote bag, jacket"
    
    total = base_price * quantity
    
    # Apply volume discount
    for threshold, discount_rate in sorted(PRICING_RULES["quantity_discounts"].items(), reverse=True):
        if quantity >= threshold:
            total *= (1 - discount_rate)
            break
    
    # Add shipping estimate
    shipping = min(
        PRICING_RULES["shipping_base"] + (PRICING_RULES["shipping_per_item"] * quantity),
        PRICING_RULES["max_shipping"]
    )
    total += shipping
    
    return f"Estimated price for {quantity} {product_type}(s): ${total:,.2f} (includes shipping, excludes customization)"


@tool
def get_product_prices() -> str:
    """Get a list of all products and their base prices.
    
    Returns:
        Formatted string with product prices
    """
    products = {
        "T-Shirt": 10.00,
        "Polo": 15.00,
        "Hoodie": 25.00,
        "Cap": 8.00,
        "Mug": 12.00,
        "Tote Bag": 7.00,
        "Jacket": 40.00,
    }
    
    lines = ["PRODUCT PRICE LIST", "=" * 30]
    for product, price in products.items():
        lines.append(f"{product}: ${price:.2f} per unit")
    
    lines.append("")
    lines.append("CUSTOMIZATION OPTIONS:")
    lines.append("- Logo Print: +$2.00/unit (setup: $25)")
    lines.append("- Embroidery: +$4.00/unit (setup: $50)")
    lines.append("- Screen Print: +$1.50/unit (setup: $35)")
    lines.append("- DTG: +$3.00/unit (no setup fee)")
    
    lines.append("")
    lines.append("VOLUME DISCOUNTS:")
    lines.append("- 100+ units: 5% off")
    lines.append("- 500+ units: 10% off")
    lines.append("- 1000+ units: 15% off")
    
    return "\n".join(lines)
