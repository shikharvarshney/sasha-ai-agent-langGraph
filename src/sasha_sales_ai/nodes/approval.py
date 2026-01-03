"""Approval handling nodes"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..config import get_settings
from ..utils.approval_handler import ApprovalHandler
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.approval")


def check_approval(state: FlowState) -> dict[str, Any]:
    """Check if the quote requires approval.
    
    This node:
    1. Checks the total amount against approval threshold
    2. Determines if manual approval is needed
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields with approval requirement
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="check_approval",
        tags=["node", "approval", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Checking approval requirement for lead {lead_id}")
        
        settings = get_settings()
        handler = ApprovalHandler(approval_threshold=settings.approval_threshold)
        
        total_amount = state.get("total_amount", 0)
        
        needs_approval = handler.needs_approval(total_amount, lead_id)
        
        logger.info(
            f"Lead {lead_id}: amount=${total_amount:,.2f}, "
            f"needs_approval={needs_approval}"
        )
        
        return {
            "needs_approval": needs_approval,
            "current_node": "check_approval",
        }


def request_approval(state: FlowState) -> dict[str, Any]:
    """Request approval for a high-value quote.
    
    This node:
    1. Creates an approval request
    2. Sets status to pending approval
    3. This is an interrupt point - flow will pause here
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="request_approval",
        tags=["node", "approval_request", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Requesting approval for lead {lead_id}")
        
        settings = get_settings()
        handler = ApprovalHandler(approval_threshold=settings.approval_threshold)
        
        # Create approval request
        approval_id = handler.request_approval(
            lead_id=lead_id,
            customer_email=state.get("email_from", ""),
            total_amount=state.get("total_amount", 0),
            order_details={
                "requirements": state.get("requirements", {}),
                "price_quote": state.get("price_quote", {}),
                "pricing_explanation": state.get("pricing_explanation", ""),
            },
        )
        
        logger.info(f"Approval request created: {approval_id}")
        
        # This is where the flow will interrupt and wait for approval
        return {
            "status": FlowStatus.APPROVAL_PENDING,
            "approval_notes": f"Approval request: {approval_id}",
            "current_node": "request_approval",
        }


def process_approval_decision(state: FlowState) -> dict[str, Any]:
    """Process the approval decision after interrupt resume.
    
    This node is called after the flow resumes from an interrupt.
    The approval decision should be in the state.
    
    Args:
        state: Current flow state with approval decision
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="process_approval_decision",
        tags=["node", "approval_decision", lead_id],
        metadata={"lead_id": lead_id},
    ):
        approved = state.get("approved")
        approval_notes = state.get("approval_notes", "")
        
        logger.info(
            f"Processing approval decision for {lead_id}: "
            f"approved={approved}, notes={approval_notes}"
        )
        
        if approved is True:
            return {
                "status": FlowStatus.PRICING,  # Continue to send quote
                "current_node": "process_approval_decision",
            }
        elif approved is False:
            return {
                "status": FlowStatus.REJECTED,
                "current_node": "process_approval_decision",
            }
        else:
            # Still pending
            return {
                "status": FlowStatus.APPROVAL_PENDING,
                "current_node": "process_approval_decision",
            }

