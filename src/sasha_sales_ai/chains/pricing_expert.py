"""Pricing expert chain using LangChain LCEL"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..config import get_settings

logger = logging.getLogger("sasha_sales_ai.chains.pricing_expert")

PRICING_EXPERT_SYSTEM_PROMPT = """You are a pricing expert for a promotional products company.
Your role is to explain pricing to customers in a clear, transparent, and professional manner.

Our Product Catalog:
- T-Shirts: Base $10.00 (min 10, max 10000 units)
- Polos: Base $15.00 (min 10, max 10000 units)
- Hoodies: Base $25.00 (min 10, max 5000 units)
- Caps: Base $8.00 (min 10, max 10000 units)
- Mugs: Base $12.00 (min 10, max 5000 units)
- Tote Bags: Base $7.00 (min 10, max 10000 units)
- Jackets: Base $40.00 (min 10, max 1000 units)

Customization Options:
- Logo printing: +$2.00/unit
- Embroidery: +$4.00/unit  
- Screen printing: +$1.50/unit
- DTG (Direct to Garment): +$3.00/unit

You should:
- Break down costs clearly
- Explain any volume discounts applied
- Justify any surcharges (rush fees, etc.)
- Highlight value propositions
- Be transparent about pricing structure

Always maintain a helpful and professional tone."""

PRICING_EXPLANATION_TEMPLATE = """Generate a clear pricing explanation for the customer.

Customer Request:
- Product: {product_type}
- Quantity: {quantity} units
- Customizations: {customizations}
- Timeline: {timeline_days} days

Pricing Breakdown:
{pricing_breakdown}

Total Amount: ${total_amount}

Generate a customer-friendly explanation that:
1. Summarizes the order
2. Explains each line item (base price, customization, setup fees)
3. Highlights any volume discounts (5% at 100+, 10% at 500+, 15% at 1000+)
4. Explains any surcharges (like rush fees for orders under 7 days)
5. Provides the final total clearly

Return as JSON:
{{
    "summary": "brief summary of the pricing",
    "explanation": "detailed customer-friendly explanation",
    "highlights": ["key points to emphasize"],
    "value_proposition": "why this is good value for the customer"
}}"""


NEGOTIATION_RESPONSE_TEMPLATE = """The customer is asking about pricing modifications.

Original Quote:
{original_quote}

Customer's Request:
{customer_request}

Our Pricing Policies:
- Volume discounts are automatic:
  * 5% discount at 100+ units
  * 10% discount at 500+ units
  * 15% discount at 1000+ units
- Rush fees apply for orders under 7 days
- Customizations have fixed per-unit costs
- Maximum negotiable discount: 20% (for very large orders only)

Generate a response addressing their pricing concerns.

Return as JSON:
{{
    "can_accommodate": true/false,
    "response_explanation": "explanation of what we can/cannot do",
    "alternative_offer": "if applicable, an alternative that might work",
    "new_total": "new total if changes were made, or null"
}}"""


def create_pricing_expert_chain():
    """Create the pricing expert chain for generating explanations.
    
    Returns:
        Runnable chain for pricing explanations
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0.2,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", PRICING_EXPERT_SYSTEM_PROMPT),
        ("human", PRICING_EXPLANATION_TEMPLATE),
    ])
    
    parser = JsonOutputParser()
    
    return prompt | llm | parser


def create_negotiation_chain():
    """Create a chain for handling pricing negotiations.
    
    Returns:
        Runnable chain for negotiation responses
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0.2,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", PRICING_EXPERT_SYSTEM_PROMPT),
        ("human", NEGOTIATION_RESPONSE_TEMPLATE),
    ])
    
    parser = JsonOutputParser()
    
    return prompt | llm | parser


def generate_pricing_explanation(
    product_type: str,
    quantity: int,
    customizations: str,
    timeline_days: int,
    pricing_breakdown: str,
    total_amount: float,
) -> dict[str, Any]:
    """Generate a customer-friendly pricing explanation.
    
    Args:
        product_type: Type of product
        quantity: Number of units
        customizations: Customization details
        timeline_days: Delivery timeline
        pricing_breakdown: Detailed pricing breakdown
        total_amount: Total quoted amount
    
    Returns:
        Dictionary with explanation and highlights
    """
    logger.info(f"Generating pricing explanation for {product_type} x {quantity}")
    
    chain = create_pricing_expert_chain()
    
    result = chain.invoke({
        "product_type": product_type,
        "quantity": quantity,
        "customizations": customizations or "None",
        "timeline_days": timeline_days or "Standard (14 days)",
        "pricing_breakdown": pricing_breakdown,
        "total_amount": f"{total_amount:,.2f}",
    })
    
    return result


def handle_pricing_negotiation(
    original_quote: str,
    customer_request: str,
) -> dict[str, Any]:
    """Handle a customer pricing negotiation request.
    
    Args:
        original_quote: The original quote details
        customer_request: What the customer is asking for
    
    Returns:
        Dictionary with negotiation response
    """
    logger.info("Handling pricing negotiation")
    
    chain = create_negotiation_chain()
    
    result = chain.invoke({
        "original_quote": original_quote,
        "customer_request": customer_request,
    })
    
    return result


def format_pricing_breakdown(pricing_data: dict[str, Any]) -> str:
    """Format pricing data into a readable breakdown.
    
    Args:
        pricing_data: Pricing calculation result
    
    Returns:
        Formatted pricing breakdown string
    """
    lines = []
    
    # Line items
    if "line_items" in pricing_data:
        lines.append("Line Items:")
        for item in pricing_data["line_items"]:
            lines.append(
                f"  - {item['description']}: ${item['total']:,.2f}"
            )
    
    # Discounts
    if pricing_data.get("discounts"):
        lines.append("\nDiscounts Applied:")
        for discount in pricing_data["discounts"]:
            lines.append(
                f"  - {discount['description']}: -${discount['amount']:,.2f}"
            )
    
    # Surcharges
    if pricing_data.get("surcharges"):
        lines.append("\nAdditional Charges:")
        for surcharge in pricing_data["surcharges"]:
            lines.append(
                f"  - {surcharge['description']}: +${surcharge['amount']:,.2f}"
            )
    
    # Totals
    lines.append(f"\nSubtotal: ${pricing_data.get('base_subtotal', 0):,.2f}")
    
    if pricing_data.get("discounts"):
        lines.append(
            f"After Discounts: ${pricing_data.get('subtotal_after_discount', 0):,.2f}"
        )
    
    if pricing_data.get("customization_total", 0) > 0:
        lines.append(
            f"Customizations: ${pricing_data.get('customization_total', 0):,.2f}"
        )
    
    if pricing_data.get("rush_surcharge", 0) > 0:
        lines.append(
            f"Rush Delivery: ${pricing_data.get('rush_surcharge', 0):,.2f}"
        )
    
    lines.append(f"\n{'='*40}")
    lines.append(f"GRAND TOTAL: ${pricing_data.get('grand_total', 0):,.2f}")
    
    return "\n".join(lines)
