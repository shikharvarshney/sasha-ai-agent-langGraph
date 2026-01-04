"""State logging utilities for debugging and monitoring workflow execution."""

import json
import logging
from functools import wraps
from typing import Any, Callable

from ..state import FlowState

logger = logging.getLogger("sasha_sales_ai.state_logger")

# Fields to include in state summary (avoid logging huge objects)
STATE_SUMMARY_FIELDS = [
    "lead_id",
    "status",
    "email_from",
    "email_subject",
    "email_type",
    "customer_intent",
    "missing_fields",
    "has_customization_request",
    "is_feasible",
    "feasibility_reason",
    "total_amount",
    "needs_approval",
    "approved",
    "customer_confirmed",
    "quote_sent",
    "order_id",
    "current_node",
    "error_message",
]


def format_state_for_logging(state: FlowState, include_requirements: bool = False) -> dict:
    """Format state for readable logging output.
    
    Args:
        state: The flow state to format
        include_requirements: Whether to include the full requirements dict
    
    Returns:
        Formatted dict suitable for logging
    """
    result = {}
    
    for field in STATE_SUMMARY_FIELDS:
        value = state.get(field)
        if value is not None:
            # Format missing_fields for readability
            if field == "missing_fields" and isinstance(value, list):
                if value:
                    formatted = []
                    for item in value[:5]:  # Limit to first 5
                        if isinstance(item, dict):
                            formatted.append(item.get("field", str(item)))
                        else:
                            formatted.append(str(item))
                    if len(value) > 5:
                        formatted.append(f"...and {len(value) - 5} more")
                    result[field] = formatted
                else:
                    result[field] = []
            else:
                result[field] = value
    
    # Include requirements summary if requested
    if include_requirements:
        requirements = state.get("requirements", {})
        if requirements:
            req_summary = {
                "product_type": requirements.get("product_type"),
                "quantity": requirements.get("quantity"),
                "delivery_address": requirements.get("delivery_address", "")[:50] if requirements.get("delivery_address") else None,
                "material": requirements.get("material"),
                "customizations": requirements.get("customizations", "")[:50] if requirements.get("customizations") else None,
            }
            # Remove None values
            result["requirements_summary"] = {k: v for k, v in req_summary.items() if v is not None}
    
    return result


def log_state_before(node_name: str, state: FlowState) -> None:
    """Log state before node execution.
    
    Args:
        node_name: Name of the node being executed
        state: Current flow state
    """
    lead_id = state.get("lead_id", "unknown")
    formatted = format_state_for_logging(state, include_requirements=True)
    
    logger.info(
        f"\n{'='*60}\n"
        f"▶ ENTERING NODE: {node_name}\n"
        f"  Lead: {lead_id}\n"
        f"{'='*60}"
    )
    logger.info(f"STATE BEFORE [{node_name}]:\n{json.dumps(formatted, indent=2, default=str)}")


def log_state_after(node_name: str, state: FlowState, updates: dict[str, Any]) -> None:
    """Log state after node execution.
    
    Args:
        node_name: Name of the node that was executed
        state: Original flow state
        updates: Updates returned by the node
    """
    lead_id = state.get("lead_id", "unknown")
    
    # Format updates for logging
    updates_formatted = {}
    for key, value in updates.items():
        if key == "requirements" and isinstance(value, dict):
            # Summarize requirements
            updates_formatted[key] = f"<dict with {len(value)} keys>"
        elif key == "price_quote" and isinstance(value, dict):
            updates_formatted[key] = f"<pricing data, total: {value.get('grand_total', 'N/A')}>"
        elif key == "missing_fields" and isinstance(value, list):
            if value:
                updates_formatted[key] = [
                    item.get("field", str(item)) if isinstance(item, dict) else str(item)
                    for item in value[:5]
                ]
                if len(value) > 5:
                    updates_formatted[key].append(f"...and {len(value) - 5} more")
            else:
                updates_formatted[key] = []
        elif isinstance(value, str) and len(value) > 200:
            updates_formatted[key] = f"{value[:200]}..."
        else:
            updates_formatted[key] = value
    
    logger.info(
        f"\n{'='*60}\n"
        f"◀ EXITING NODE: {node_name}\n"
        f"  Lead: {lead_id}\n"
        f"  New Status: {updates.get('status', 'unchanged')}\n"
        f"{'='*60}"
    )
    logger.info(f"STATE UPDATES [{node_name}]:\n{json.dumps(updates_formatted, indent=2, default=str)}")


def log_incoming_email(state: FlowState) -> None:
    """Log the incoming customer email content.
    
    Args:
        state: Flow state containing email data
    """
    lead_id = state.get("lead_id", "unknown")
    email_from = state.get("email_from", "unknown")
    email_subject = state.get("email_subject", "(no subject)")
    email_body = state.get("email_body", "")
    email_type = state.get("email_type", "new")
    
    logger.info(
        f"\n{'#'*60}\n"
        f"📧 INCOMING EMAIL ({email_type.upper()})\n"
        f"{'#'*60}\n"
        f"Lead ID: {lead_id}\n"
        f"From: {email_from}\n"
        f"Subject: {email_subject}\n"
        f"{'─'*60}\n"
        f"Body:\n{email_body}\n"
        f"{'#'*60}"
    )


def log_outgoing_email(lead_id: str, to_address: str, subject: str, body: str, email_type: str = "outgoing") -> None:
    """Log an outgoing email being sent.
    
    Args:
        lead_id: Lead identifier
        to_address: Recipient email address
        subject: Email subject
        body: Email body content
        email_type: Type of email (clarification, quote, confirmation, rejection)
    """
    logger.info(
        f"\n{'#'*60}\n"
        f"📤 OUTGOING EMAIL ({email_type.upper()})\n"
        f"{'#'*60}\n"
        f"Lead ID: {lead_id}\n"
        f"To: {to_address}\n"
        f"Subject: {subject}\n"
        f"{'─'*60}\n"
        f"Body:\n{body}\n"
        f"{'#'*60}"
    )


def with_state_logging(node_name: str):
    """Decorator to add state logging to a node function.
    
    Args:
        node_name: Name of the node for logging
    
    Returns:
        Decorated function with state logging
    """
    def decorator(func: Callable[[FlowState], dict[str, Any]]):
        @wraps(func)
        def wrapper(state: FlowState) -> dict[str, Any]:
            # Log state before execution
            log_state_before(node_name, state)
            
            # Execute the node
            result = func(state)
            
            # Log state updates after execution
            log_state_after(node_name, state, result)
            
            return result
        
        return wrapper
    return decorator

