"""Email composition chain using LangChain LCEL"""

import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..config import get_settings

logger = logging.getLogger("sasha_sales_ai.chains.email_writer")

# Base email writing prompt
EMAIL_WRITER_SYSTEM_PROMPT = """You are a professional sales email writer for a manufacturing company. 
Write clear, professional, and friendly emails that maintain a helpful tone.

Guidelines:
- Be concise but thorough
- Use professional language
- Include all necessary details
- End with a clear call to action when appropriate
- Maintain a warm, helpful tone

Return your response as JSON with:
{{
    "subject": "email subject line",
    "body": "email body content",
    "tone": "description of the tone used"
}}"""


# Quote email template
QUOTE_EMAIL_TEMPLATE = """Write a professional quote email to the customer.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Quote Details:
{quote_details}

Total Amount: ${total_amount}

Additional Context:
{additional_context}

Write a professional email presenting this quote. Include:
1. Greeting with customer name
2. Reference to their original request
3. Quote breakdown
4. Total amount prominently displayed
5. Validity period (30 days)
6. Clear next steps for confirmation
7. Professional closing"""


# Clarification email template
CLARIFICATION_EMAIL_TEMPLATE = """Write a professional email requesting additional information from the customer.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Original Request Summary:
{request_summary}

Missing Information Needed:
{missing_info}

Write a friendly email that:
1. Thanks them for their inquiry
2. Summarizes what we understood from their request
3. Clearly lists the additional information needed
4. Explains why we need this information
5. Encourages them to reply with the details"""


# Confirmation email template  
CONFIRMATION_EMAIL_TEMPLATE = """Write a professional order confirmation email.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Order Details:
- Order ID: {order_id}
- Product: {product_type}
- Quantity: {quantity}
- Total: ${total_amount}
- Estimated Delivery: {estimated_delivery}

Additional Details:
{additional_details}

Write a confirmation email that:
1. Confirms the order with excitement
2. Lists order details clearly
3. Provides the order reference number
4. States estimated delivery
5. Provides contact information for questions"""


# Rejection email template
REJECTION_EMAIL_TEMPLATE = """Write a professional but empathetic email explaining why we cannot fulfill the request.

Customer Information:
- Name: {customer_name}
- Email: {customer_email}

Rejection Reason:
{rejection_reason}

Alternatives (if any):
{alternatives}

Write a polite email that:
1. Thanks them for considering us
2. Politely explains why we cannot fulfill their request
3. Offers alternatives if available
4. Leaves the door open for future business
5. Maintains a positive tone throughout"""


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
    quote_details: str,
    total_amount: float,
    additional_context: str = "",
) -> dict[str, Any]:
    """Generate a quote email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        quote_details: Formatted quote details
        total_amount: Total quoted amount
        additional_context: Any additional context
    
    Returns:
        Dictionary with subject and body
    """
    logger.info(f"Writing quote email for {customer_email}")
    
    chain = create_email_writer_chain("quote")
    
    result = chain.invoke({
        "customer_name": customer_name or "Valued Customer",
        "customer_email": customer_email,
        "quote_details": quote_details,
        "total_amount": f"{total_amount:,.2f}",
        "additional_context": additional_context or "N/A",
    })
    
    return result


def write_clarification_email(
    customer_name: str,
    customer_email: str,
    request_summary: str,
    missing_info: list[str],
) -> dict[str, Any]:
    """Generate a clarification request email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
        request_summary: Summary of their original request
        missing_info: List of missing information items
    
    Returns:
        Dictionary with subject and body
    """
    logger.info(f"Writing clarification email for {customer_email}")
    
    chain = create_email_writer_chain("clarification")
    
    missing_formatted = "\n".join(f"- {item}" for item in missing_info)
    
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
        "additional_details": additional_details or "N/A",
    })
    
    return result


def write_rejection_email(
    customer_name: str,
    customer_email: str,
    rejection_reason: str,
    alternatives: Optional[str] = None,
) -> dict[str, Any]:
    """Generate a rejection email.
    
    Args:
        customer_name: Customer's name
        customer_email: Customer's email
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
        "rejection_reason": rejection_reason,
        "alternatives": alternatives or "Unfortunately, we don't have alternatives at this time.",
    })
    
    return result

