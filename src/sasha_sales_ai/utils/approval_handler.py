"""Approval handling utilities"""

import logging
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger("sasha_sales_ai.utils.approval")

# In-memory approval storage (would be a database in production)
_pending_approvals: dict[str, dict[str, Any]] = {}


class ApprovalHandler:
    """Handler for managing approval requests and responses"""
    
    def __init__(self, approval_threshold: float = 10000.0):
        """Initialize the approval handler.
        
        Args:
            approval_threshold: Amount above which approval is required
        """
        self.approval_threshold = approval_threshold
    
    def needs_approval(self, total_amount: float, lead_id: str) -> bool:
        """Check if an order requires approval.
        
        Args:
            total_amount: Total order amount
            lead_id: Lead ID for the order
        
        Returns:
            True if approval is required
        """
        # Always require approval for amounts above threshold
        if total_amount >= self.approval_threshold:
            logger.info(f"Lead {lead_id}: Approval required (${total_amount:,.2f} >= ${self.approval_threshold:,.2f})")
            return True
        
        logger.info(f"Lead {lead_id}: Auto-approved (${total_amount:,.2f} < ${self.approval_threshold:,.2f})")
        return False
    
    def request_approval(
        self,
        lead_id: str,
        customer_email: str,
        total_amount: float,
        order_details: dict[str, Any],
    ) -> str:
        """Create an approval request.
        
        Args:
            lead_id: Lead ID
            customer_email: Customer's email
            total_amount: Total order amount
            order_details: Order details dictionary
        
        Returns:
            Approval request ID
        """
        approval_id = f"APR-{lead_id}"
        
        _pending_approvals[approval_id] = {
            "approval_id": approval_id,
            "lead_id": lead_id,
            "customer_email": customer_email,
            "total_amount": total_amount,
            "order_details": order_details,
            "status": "pending",
            "requested_at": datetime.now().isoformat(),
            "approved_at": None,
            "approved_by": None,
            "approval_notes": None,
        }
        
        logger.info(f"Approval request created: {approval_id}")
        
        return approval_id
    
    def approve(
        self,
        lead_id: str,
        approved_by: str = "system",
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Approve a pending request.
        
        Args:
            lead_id: Lead ID to approve
            approved_by: Who approved the request
            notes: Optional approval notes
        
        Returns:
            Updated approval record
        """
        approval_id = f"APR-{lead_id}"
        
        if approval_id not in _pending_approvals:
            raise ValueError(f"No pending approval found for lead {lead_id}")
        
        approval = _pending_approvals[approval_id]
        approval["status"] = "approved"
        approval["approved_at"] = datetime.now().isoformat()
        approval["approved_by"] = approved_by
        approval["approval_notes"] = notes
        
        logger.info(f"Approval {approval_id} approved by {approved_by}")
        
        return approval
    
    def reject(
        self,
        lead_id: str,
        rejected_by: str = "system",
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Reject a pending request.
        
        Args:
            lead_id: Lead ID to reject
            rejected_by: Who rejected the request
            reason: Rejection reason
        
        Returns:
            Updated approval record
        """
        approval_id = f"APR-{lead_id}"
        
        if approval_id not in _pending_approvals:
            raise ValueError(f"No pending approval found for lead {lead_id}")
        
        approval = _pending_approvals[approval_id]
        approval["status"] = "rejected"
        approval["rejected_at"] = datetime.now().isoformat()
        approval["rejected_by"] = rejected_by
        approval["rejection_reason"] = reason
        
        logger.info(f"Approval {approval_id} rejected by {rejected_by}: {reason}")
        
        return approval
    
    def get_approval_status(self, lead_id: str) -> Optional[dict[str, Any]]:
        """Get the approval status for a lead.
        
        Args:
            lead_id: Lead ID to check
        
        Returns:
            Approval record or None if not found
        """
        approval_id = f"APR-{lead_id}"
        return _pending_approvals.get(approval_id)
    
    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Get all pending approval requests.
        
        Returns:
            List of pending approval records
        """
        return [
            approval for approval in _pending_approvals.values()
            if approval["status"] == "pending"
        ]
    
    def is_approved(self, lead_id: str) -> Optional[bool]:
        """Check if a lead has been approved.
        
        Args:
            lead_id: Lead ID to check
        
        Returns:
            True if approved, False if rejected, None if pending/not found
        """
        approval = self.get_approval_status(lead_id)
        
        if approval is None:
            return None
        
        if approval["status"] == "approved":
            return True
        elif approval["status"] == "rejected":
            return False
        else:
            return None  # Still pending

