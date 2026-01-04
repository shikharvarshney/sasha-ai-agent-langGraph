"""Email composition chain using LangChain LCEL"""

import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..config import get_settings

logger = logging.getLogger("sasha_sales_ai.chains.email_writer")

# Base email writing prompt
EMAIL_WRITER_SYSTEM_PROMPT = """You are a professional sales email writer for a promotional products company.
Write clear, professional, and friendly emails that maintain a helpful tone.

Guidelines:
- Be concise but thorough
- Use professional language
- Include all necessary details
- End with a clear call to action when appropriate
- Maintain a warm, helpful tone
- Never be pushy or aggressive

Return your response as JSON with:
{{
    "subject": "email subject line",
    "body": "email body content"
}}"""


# Clarification email template - CRITICAL: Only ask for missing info
CLARIFICATION_EMAIL_TEMPLATE = """Write a friendly email to request ONLY the missing information from the customer.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

What we understood from their request:
{request_summary}

Missing Information that we NEED:
{missing_info}

CRITICAL RULES:
1. ONLY ask for items in the "Missing Information" list - NOTHING ELSE!
2. DO NOT ask for confirmation or re-confirmation of any information
3. DO NOT ask for things already provided (if not in missing list, we have it)
4. If a field is NOT in the Missing Information list, assume we already have it
5. Be specific about what you need and why

Write a professional email that:
1. Thanks them for reaching out and providing information so far
2. Lists ONLY the specific missing items from the missing info list
3. For each missing item, briefly explain why we need it
4. Ends with a helpful, encouraging closing

DO NOT:
- Ask for delivery address if not in missing list
- Ask for size distribution if not in missing list
- Ask for material if not in missing list
- Ask customers to "confirm" anything - just ask for missing info
- Add any extra questions not in the missing list"""


# Quote email template
QUOTE_EMAIL_TEMPLATE = """Write a professional quote email to the customer.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Order Summary:
{order_summary}

Quote Details:
{quote_details}

Total Amount: ${total_amount}

Pricing Breakdown:
{pricing_breakdown}

Write a professional email presenting this quote that includes:
1. Warm greeting with customer name
2. Thank them for their inquiry
3. Summarize our understanding of their requirements
4. Present the quote with clear pricing breakdown
5. Total amount prominently displayed
6. Validity period (30 days)
7. Clear next steps to confirm the order
8. Professional closing

Make the pricing easy to understand and highlight any value or included services."""


# Confirmation email template  
CONFIRMATION_EMAIL_TEMPLATE = """Write a professional order confirmation email.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Order Details:
- Order ID: {order_id}
- Product: {product_type}
- Quantity: {quantity}
- Customization: {customization_details}
- Total: ${total_amount}
- Estimated Delivery: {estimated_delivery}
- Delivery Address: {delivery_address}

Additional Details:
{additional_details}

Write a confirmation email that:
1. Confirms the order with enthusiasm
2. Displays the order reference number prominently
3. Lists all order details clearly
4. States estimated delivery date
5. Provides contact information for questions
6. Thanks them for their business
7. Creates excitement about their upcoming order"""


# Rejection email template
REJECTION_EMAIL_TEMPLATE = """Write a professional but empathetic email explaining why we cannot fulfill the request.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Original Request:
{original_request}

Rejection Reason:
{rejection_reason}

Alternatives (if any):
{alternatives}

Write a polite email that:
1. Thanks them for considering us
2. Acknowledges their specific request
3. Politely explains why we cannot fulfill their exact request
4. Offers alternatives if available
5. Leaves the door open for future business
6. Maintains a positive, helpful tone throughout

Never make the customer feel bad for their request."""


def create_email_writer_chain(email_type: str):
    """Create an email writer chain for a specific email type.
    
    Args:
        email_type: Type of email (quote, clarification, confirmation, rejection)
    
    Returns:
        Runnable chain for email generation
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0.3,  # Slightly higher for more natural writing
    )
    
    templates = {
        "quote": QUOTE_EMAIL_TEMPLATE,
        "clarification": CLARIFICATION_EMAIL_TEMPLATE,
        "confirmation": CONFIRMATION_EMAIL_TEMPLATE,
        "rejection": REJECTION_EMAIL_TEMPLATE,
    }
    
    template = templates.get(email_type, QUOTE_EMAIL_TEMPLATE)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", EMAIL_WRITER_SYSTEM_PROMPT),
        ("human", template),
    ])
    
    parser = JsonOutputParser()
    
    return prompt | llm | parser


def write_quote_email(
    customer_name: str,
    customer_email: str,
    order_summary: str,
    quote_details: str,
    total_amount: float,
    pricing_breakdown: str = "",
) -> dict[str, Any]:
    """Generate a quote email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        order_summary: Summary of what they requested
        quote_details: Formatted quote details
        total_amount: Total quoted amount
        pricing_breakdown: Breakdown of pricing
    
    Returns:
        Dictionary with subject and body
    """
    logger.info(f"Writing quote email for {customer_email}")
    
    chain = create_email_writer_chain("quote")
    
    result = chain.invoke({
        "customer_name": customer_name or "Valued Customer",
        "customer_email": customer_email,
        "order_summary": order_summary,
        "quote_details": quote_details,
        "total_amount": f"{total_amount:,.2f}",
        "pricing_breakdown": pricing_breakdown or "See quote details above",
    })
    
    return result


def write_clarification_email(
    customer_name: str,
    customer_email: str,
    request_summary: str,
    missing_info: list[dict[str, str]],
) -> dict[str, Any]:
    """Generate a clarification request email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        request_summary: Summary of their original request
        missing_info: List of missing information items with descriptions
    
    Returns:
        Dictionary with subject and body
    """
    logger.info(f"Writing clarification email for {customer_email}")
    
    chain = create_email_writer_chain("clarification")
    
    # Format missing info clearly
    if isinstance(missing_info, list):
        if missing_info and isinstance(missing_info[0], dict):
            missing_formatted = "\n".join(
                f"- {item.get('field', item)}: {item.get('description', 'Please provide this information')}" 
                for item in missing_info
            )
        else:
            missing_formatted = "\n".join(f"- {item}" for item in missing_info)
    else:
        missing_formatted = str(missing_info)
    
    result = chain.invoke({
        "customer_name": customer_name or "Valued Customer",
        "customer_email": customer_email,
        "request_summary": request_summary,
        "missing_info": missing_formatted,
    })
    
    return result


def write_confirmation_email(
    customer_name: str,
    customer_email: str,
    order_id: str,
    product_type: str,
    quantity: int,
    total_amount: float,
    estimated_delivery: str,
    delivery_address: str = "",
    customization_details: str = "",
    additional_details: str = "",
) -> dict[str, Any]:
    """Generate an order confirmation email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        order_id: Order reference number
        product_type: Type of product
        quantity: Number of units
        total_amount: Total order amount
        estimated_delivery: Estimated delivery date
        delivery_address: Shipping address
        customization_details: Customization info
        additional_details: Any additional details
    
    Returns:
        Dictionary with subject and body
    """
    logger.info(f"Writing confirmation email for order {order_id}")
    
    chain = create_email_writer_chain("confirmation")
    
    result = chain.invoke({
        "customer_name": customer_name or "Valued Customer",
        "customer_email": customer_email,
        "order_id": order_id,
        "product_type": product_type,
        "quantity": quantity,
        "total_amount": f"{total_amount:,.2f}",
        "estimated_delivery": estimated_delivery,
        "delivery_address": delivery_address or "To be confirmed",
        "customization_details": customization_details or "Standard (no customization)",
        "additional_details": additional_details or "N/A",
    })
    
    return result


def write_rejection_email(
    customer_name: str,
    customer_email: str,
    original_request: str,
    rejection_reason: str,
    alternatives: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a rejection email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        original_request: Summary of their request
        rejection_reason: Reason for rejection
        alternatives: Optional alternative suggestions
    
    Returns:
        Dictionary with subject and body
    """
    logger.info(f"Writing rejection email for {customer_email}")
    
    chain = create_email_writer_chain("rejection")
    
    result = chain.invoke({
        "customer_name": customer_name or "Valued Customer",
        "customer_email": customer_email,
        "original_request": original_request,
        "rejection_reason": rejection_reason,
        "alternatives": alternatives or "Unfortunately, we don't have alternatives for this specific request at this time. However, please feel free to reach out for other promotional product needs.",
    })
    
    return result
