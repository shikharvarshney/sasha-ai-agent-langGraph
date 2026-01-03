"""FlowState TypedDict definition for LangGraph"""

from typing import TypedDict, Optional, Any


class FlowState(TypedDict, total=False):
    """State definition for the sales workflow graph
    
    This TypedDict defines all the state that flows through the LangGraph
    workflow. Using total=False makes all fields optional.
    """

    # Lead identification
    lead_id: str
    status: str  # new, understanding, clarifying, feasibility, pricing, 
                 # approval_pending, quote_sent, order_placed, completed, rejected

    # Email data
    email_from: str
    email_subject: str
    email_body: str
    email_type: str  # "new" or "reply"
    thread_history: str

    # Analysis results
    requirements: dict[str, Any]
    missing_fields: list[str]
    customer_intent: str  # new_inquiry, clarification, confirmation, 
                          # rejection, modification, question

    # Feasibility
    is_feasible: Optional[bool]
    feasibility_reason: str
    alternatives: str

    # Pricing
    price_quote: dict[str, Any]
    pricing_explanation: str
    total_amount: float

    # Approval & Order
    needs_approval: bool
    approved: Optional[bool]
    approval_notes: str
    order_id: str
    customer_confirmed: bool

    # Flow tracking
    quote_sent: bool
    feasibility_checked: bool
    current_node: str

    # Email responses
    outgoing_email_subject: str
    outgoing_email_body: str

    # Error handling
    error_message: str
    error_node: str


# Status constants for type safety
class FlowStatus:
    """Constants for flow status values"""
    NEW = "new"
    UNDERSTANDING = "understanding"
    CLARIFYING = "clarifying"
    FEASIBILITY = "feasibility"
    PRICING = "pricing"
    APPROVAL_PENDING = "approval_pending"
    QUOTE_SENT = "quote_sent"
    ORDER_PLACED = "order_placed"
    COMPLETED = "completed"
    REJECTED = "rejected"
    ERROR = "error"


# Customer intent constants
class CustomerIntent:
    """Constants for customer intent classification"""
    NEW_INQUIRY = "new_inquiry"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    REJECTION = "rejection"
    MODIFICATION = "modification"
    QUESTION = "question"


def create_initial_state(
    lead_id: str,
    email_from: str,
    email_subject: str,
    email_body: str,
    email_type: str = "new",
) -> FlowState:
    """Create an initial flow state from email data
    
    Args:
        lead_id: Unique identifier for the lead
        email_from: Sender email address
        email_subject: Email subject line
        email_body: Email body content
        email_type: Type of email ("new" or "reply")
    
    Returns:
        Initialized FlowState dictionary
    """
    return FlowState(
        lead_id=lead_id,
        status=FlowStatus.NEW,
        email_from=email_from,
        email_subject=email_subject,
        email_body=email_body,
        email_type=email_type,
        thread_history="",
        requirements={},
        missing_fields=[],
        customer_intent="",
        is_feasible=None,
        feasibility_reason="",
        alternatives="",
        price_quote={},
        pricing_explanation="",
        total_amount=0.0,
        needs_approval=False,
        approved=None,
        approval_notes="",
        order_id="",
        customer_confirmed=False,
        quote_sent=False,
        feasibility_checked=False,
        current_node="",
        outgoing_email_subject="",
        outgoing_email_body="",
        error_message="",
        error_node="",
    )

