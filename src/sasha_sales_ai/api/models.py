"""API request and response models"""

from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


class EmailWebhook(BaseModel):
    """Incoming email webhook payload"""
    
    lead_id: Optional[str] = Field(
        default=None,
        description="Lead ID for existing leads, auto-generated for new"
    )
    from_email: EmailStr = Field(
        ...,
        description="Sender email address"
    )
    subject: str = Field(
        ...,
        description="Email subject line"
    )
    body: str = Field(
        ...,
        description="Email body content"
    )
    email_type: str = Field(
        default="new",
        description="Type of email: 'new' or 'reply'"
    )
    
    def to_state(self) -> dict[str, Any]:
        """Convert to flow state format"""
        import uuid
        return {
            "lead_id": self.lead_id or f"lead-{uuid.uuid4().hex[:8]}",
            "email_from": self.from_email,
            "email_subject": self.subject,
            "email_body": self.body,
            "email_type": self.email_type,
        }


class ApprovalRequest(BaseModel):
    """Approval action request"""
    
    approved_by: str = Field(
        default="system",
        description="Who is approving/rejecting"
    )
    notes: str = Field(
        default="",
        description="Approval or rejection notes"
    )


class LeadStatus(BaseModel):
    """Lead status response"""
    
    lead_id: str
    status: str
    email_from: Optional[str] = None
    email_subject: Optional[str] = None
    total_amount: Optional[float] = None
    order_id: Optional[str] = None
    needs_approval: Optional[bool] = None
    approved: Optional[bool] = None
    current_node: Optional[str] = None
    error_message: Optional[str] = None
    
    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "LeadStatus":
        """Create from flow state"""
        return cls(
            lead_id=state.get("lead_id", ""),
            status=state.get("status", "unknown"),
            email_from=state.get("email_from"),
            email_subject=state.get("email_subject"),
            total_amount=state.get("total_amount"),
            order_id=state.get("order_id"),
            needs_approval=state.get("needs_approval"),
            approved=state.get("approved"),
            current_node=state.get("current_node"),
            error_message=state.get("error_message"),
        )


class LeadListResponse(BaseModel):
    """Response for listing leads"""
    
    leads: list[dict[str, Any]]
    total: int


class FlowResponse(BaseModel):
    """Response after running a flow"""
    
    lead_id: str
    status: str
    message: str
    details: Optional[dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str
    version: str
    langsmith_enabled: bool


class PendingApproval(BaseModel):
    """Pending approval item"""
    
    lead_id: str
    customer_email: str
    total_amount: float
    status: str
    requested_at: Optional[str] = None

