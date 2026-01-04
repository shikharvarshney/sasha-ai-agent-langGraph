"""FastAPI routes with LangSmith tracing"""

import logging
from typing import Optional
import asyncio

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from .models import (
    EmailWebhook,
    ApprovalRequest,
    LeadStatus,
    LeadListResponse,
    FlowResponse,
    HealthResponse,
    PendingApproval,
)
from ..flow_manager import FlowManager, get_flow_manager
from ..state import FlowStatus
from ..config import get_settings
from ..utils.langsmith_helpers import get_tracing_context
from .. import __version__

logger = logging.getLogger("sasha_sales_ai.api.routes")

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Health check endpoint with Redis status"""
    settings = get_settings()
    
    # Get flow manager health
    fm_health = flow_manager.health_check()
    
    # Determine overall status
    overall_status = "healthy" if fm_health["redis_connected"] else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=__version__,
        langsmith_enabled=bool(settings.langsmith_api_key),
        redis_connected=fm_health["redis_connected"],
        lead_count=fm_health["lead_count"],
        checkpointer_type=fm_health["checkpointer_type"],
    )


@router.post("/webhook/email", response_model=FlowResponse)
async def email_webhook(
    email_data: EmailWebhook,
    background_tasks: BackgroundTasks,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Handle incoming email webhook.
    
    Processes new emails and replies through the sales workflow.
    """
    with get_tracing_context(
        name="email_webhook",
        tags=["webhook", "api"],
        metadata={"from": email_data.from_email, "type": email_data.email_type},
    ):
        logger.info(f"Received email webhook from {email_data.from_email}")
        
        try:
            # Convert to state format
            state_data = email_data.to_state()
            lead_id = state_data["lead_id"]
            
            # Get or create state
            state = flow_manager.get_or_create_state(
                lead_id=lead_id,
                email_from=state_data["email_from"],
                email_subject=state_data["email_subject"],
                email_body=state_data["email_body"],
                email_type=state_data["email_type"],
            )
            
            # Run flow asynchronously
            result = await flow_manager.run_flow(lead_id, state)
            
            return FlowResponse(
                lead_id=lead_id,
                status=result.get("status", "unknown"),
                message=f"Email processed successfully",
                details={
                    "current_node": result.get("current_node"),
                    "needs_approval": result.get("needs_approval"),
                    "total_amount": result.get("total_amount"),
                },
            )
            
        except Exception as e:
            logger.error(f"Error processing email webhook: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/reply", response_model=FlowResponse)
async def reply_webhook(
    email_data: EmailWebhook,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Handle customer reply webhook.
    
    Processes customer replies to quotes or clarification requests.
    """
    with get_tracing_context(
        name="reply_webhook",
        tags=["webhook", "reply", "api"],
        metadata={"from": email_data.from_email},
    ):
        logger.info(f"Received reply webhook from {email_data.from_email}")
        
        if not email_data.lead_id:
            raise HTTPException(
                status_code=400,
                detail="lead_id is required for reply webhooks"
            )
        
        try:
            # Force email type to reply
            state_data = email_data.to_state()
            state_data["email_type"] = "reply"
            lead_id = state_data["lead_id"]
            
            # Get existing state
            existing_state = flow_manager.get_state(lead_id)
            if not existing_state:
                raise HTTPException(
                    status_code=404,
                    detail=f"Lead {lead_id} not found"
                )
            
            # Update state with new email data
            existing_state.update({
                "email_from": state_data["email_from"],
                "email_subject": state_data["email_subject"],
                "email_body": state_data["email_body"],
                "email_type": "reply",
            })
            
            # Run flow
            result = await flow_manager.run_flow(lead_id, existing_state)
            
            return FlowResponse(
                lead_id=lead_id,
                status=result.get("status", "unknown"),
                message="Reply processed successfully",
                details={
                    "customer_intent": result.get("customer_intent"),
                    "current_node": result.get("current_node"),
                },
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing reply webhook: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/lead/{lead_id}", response_model=LeadStatus)
async def get_lead(
    lead_id: str,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Get lead status and details"""
    with get_tracing_context(
        name="get_lead",
        tags=["api", "read"],
        metadata={"lead_id": lead_id},
    ):
        state = flow_manager.get_state(lead_id)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {lead_id} not found"
            )
        
        return LeadStatus.from_state(state)


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    status: Optional[str] = None,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """List all leads, optionally filtered by status"""
    with get_tracing_context(
        name="list_leads",
        tags=["api", "read"],
        metadata={"status_filter": status},
    ):
        leads = flow_manager.list_leads(status=status)
        
        return LeadListResponse(
            leads=leads,
            total=len(leads),
        )


@router.get("/approvals/pending", response_model=list[PendingApproval])
async def get_pending_approvals(
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Get all leads pending approval"""
    with get_tracing_context(
        name="get_pending_approvals",
        tags=["api", "approval"],
    ):
        leads = flow_manager.get_pending_approvals()
        
        return [
            PendingApproval(
                lead_id=lead["lead_id"],
                customer_email=lead.get("email_from", ""),
                total_amount=lead.get("total_amount", 0),
                status=lead.get("status", ""),
                requested_at=lead.get("updated_at"),
            )
            for lead in leads
        ]


@router.post("/approve/{lead_id}", response_model=FlowResponse)
async def approve_lead(
    lead_id: str,
    request: ApprovalRequest,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Approve a pending lead"""
    with get_tracing_context(
        name="approve_lead",
        tags=["api", "approval"],
        metadata={"lead_id": lead_id, "approved_by": request.approved_by},
    ):
        logger.info(f"Approving lead {lead_id}")
        
        try:
            result = flow_manager.approve_lead(
                lead_id=lead_id,
                approved_by=request.approved_by,
                notes=request.notes,
            )
            
            return FlowResponse(
                lead_id=lead_id,
                status=result.get("status", "unknown"),
                message="Lead approved and quote sent",
                details={
                    "current_node": result.get("current_node"),
                    "quote_sent": result.get("quote_sent"),
                },
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error approving lead {lead_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject/{lead_id}", response_model=FlowResponse)
async def reject_lead(
    lead_id: str,
    request: ApprovalRequest,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Reject a pending lead"""
    with get_tracing_context(
        name="reject_lead",
        tags=["api", "approval", "rejection"],
        metadata={"lead_id": lead_id, "rejected_by": request.approved_by},
    ):
        logger.info(f"Rejecting lead {lead_id}")
        
        try:
            result = flow_manager.reject_lead(
                lead_id=lead_id,
                rejected_by=request.approved_by,
                reason=request.notes,
            )
            
            return FlowResponse(
                lead_id=lead_id,
                status=result.get("status", "unknown"),
                message="Lead rejected",
                details={
                    "current_node": result.get("current_node"),
                },
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error rejecting lead {lead_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/lead/{lead_id}")
async def delete_lead(
    lead_id: str,
    flow_manager: FlowManager = Depends(get_flow_manager),
):
    """Delete a lead (for testing/cleanup)"""
    with get_tracing_context(
        name="delete_lead",
        tags=["api", "delete"],
        metadata={"lead_id": lead_id},
    ):
        state = flow_manager.get_state(lead_id)
        
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Lead {lead_id} not found"
            )
        
        # Delete from Redis storage
        deleted = flow_manager.delete_lead(lead_id)
        
        if deleted:
            return {"message": f"Lead {lead_id} deleted"}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete lead {lead_id}"
            )

