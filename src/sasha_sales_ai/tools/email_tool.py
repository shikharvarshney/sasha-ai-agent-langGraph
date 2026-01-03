"""Email sending tool"""

import logging
from typing import Optional
from langchain_core.tools import tool

logger = logging.getLogger("sasha_sales_ai.tools.email")


@tool
def send_email(
    to_address: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    reply_to_thread: Optional[str] = None,
) -> str:
    """Send an email to a customer or internal recipient.
    
    Args:
        to_address: Recipient email address
        subject: Email subject line
        body: Email body content (supports HTML)
        cc: Optional CC recipient
        reply_to_thread: Optional thread ID to reply to
    
    Returns:
        Status message indicating success or failure
    """
    logger.info(f"Sending email to {to_address}: {subject}")
    
    # In a real implementation, this would integrate with an email service
    # like SendGrid, AWS SES, or a company's SMTP server
    
    try:
        # Simulate email sending
        email_data = {
            "to": to_address,
            "subject": subject,
            "body": body,
            "cc": cc,
            "thread_id": reply_to_thread,
        }
        
        # Log the email for debugging
        logger.debug(f"Email data: {email_data}")
        
        # In production, replace with actual email service call:
        # response = email_service.send(email_data)
        
        return f"Email sent successfully to {to_address}"
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Failed to send email: {str(e)}"


@tool
def send_quote_email(
    to_address: str,
    customer_name: str,
    quote_details: str,
    total_amount: float,
    validity_days: int = 30,
) -> str:
    """Send a formal price quote email to a customer.
    
    Args:
        to_address: Customer email address
        customer_name: Customer's name for personalization
        quote_details: Detailed quote breakdown
        total_amount: Total quoted amount
        validity_days: Number of days the quote is valid
    
    Returns:
        Status message indicating success or failure
    """
    subject = f"Your Quote Request - ${total_amount:,.2f}"
    
    body = f"""
Dear {customer_name},

Thank you for your inquiry. Please find below our quotation for your request:

{quote_details}

Total Amount: ${total_amount:,.2f}

This quote is valid for {validity_days} days from the date of this email.

To proceed with this order, simply reply to this email with your confirmation.
If you have any questions or would like to discuss modifications, please don't hesitate to reach out.

Best regards,
Sasha Sales AI
"""
    
    return send_email.invoke({
        "to_address": to_address,
        "subject": subject,
        "body": body.strip(),
    })


@tool
def send_clarification_email(
    to_address: str,
    customer_name: str,
    missing_information: list[str],
    original_request_summary: str,
) -> str:
    """Send an email requesting additional information from the customer.
    
    Args:
        to_address: Customer email address
        customer_name: Customer's name for personalization
        missing_information: List of information items needed
        original_request_summary: Summary of the original request
    
    Returns:
        Status message indicating success or failure
    """
    subject = "Additional Information Needed for Your Quote Request"
    
    missing_items = "\n".join(f"  - {item}" for item in missing_information)
    
    body = f"""
Dear {customer_name},

Thank you for reaching out regarding your request:

"{original_request_summary}"

To provide you with an accurate quote, we need a few more details:

{missing_items}

Please reply to this email with the requested information, and we'll get back to you with a comprehensive quote shortly.

Best regards,
Sasha Sales AI
"""
    
    return send_email.invoke({
        "to_address": to_address,
        "subject": subject,
        "body": body.strip(),
    })


@tool
def send_confirmation_email(
    to_address: str,
    customer_name: str,
    order_id: str,
    order_details: str,
    estimated_delivery: str,
) -> str:
    """Send an order confirmation email to the customer.
    
    Args:
        to_address: Customer email address
        customer_name: Customer's name for personalization
        order_id: The order reference number
        order_details: Details of the confirmed order
        estimated_delivery: Estimated delivery date/timeframe
    
    Returns:
        Status message indicating success or failure
    """
    subject = f"Order Confirmation - #{order_id}"
    
    body = f"""
Dear {customer_name},

Great news! Your order has been confirmed.

Order Reference: #{order_id}

Order Details:
{order_details}

Estimated Delivery: {estimated_delivery}

You will receive updates on your order status. If you have any questions, please reply to this email with your order reference number.

Thank you for your business!

Best regards,
Sasha Sales AI
"""
    
    return send_email.invoke({
        "to_address": to_address,
        "subject": subject,
        "body": body.strip(),
    })


@tool
def send_rejection_email(
    to_address: str,
    customer_name: str,
    rejection_reason: str,
    alternatives: Optional[str] = None,
) -> str:
    """Send a polite rejection email when a request cannot be fulfilled.
    
    Args:
        to_address: Customer email address
        customer_name: Customer's name for personalization
        rejection_reason: Reason why the request cannot be fulfilled
        alternatives: Optional alternative suggestions
    
    Returns:
        Status message indicating success or failure
    """
    subject = "Regarding Your Recent Request"
    
    alternatives_section = ""
    if alternatives:
        alternatives_section = f"""

However, we may be able to help with the following alternatives:

{alternatives}
"""
    
    body = f"""
Dear {customer_name},

Thank you for considering us for your needs.

After careful review, we regret to inform you that we are unable to fulfill your request at this time due to the following reason:

{rejection_reason}
{alternatives_section}

We value your interest and hope to assist you with future inquiries.

Best regards,
Sasha Sales AI
"""
    
    return send_email.invoke({
        "to_address": to_address,
        "subject": subject,
        "body": body.strip(),
    })

