"""Email ingestion node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus
from ..storage.rag_storage import get_rag_storage
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.ingest")


def ingest_email(state: FlowState) -> dict[str, Any]:
    """Ingest an incoming email and prepare it for processing.
    
    This node:
    1. Validates the email data
    2. Stores it in RAG storage for context
    3. Updates the flow status
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="ingest_email",
        tags=["node", "ingest", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Ingesting email for lead {lead_id}")
        
        # Validate required email fields
        email_from = state.get("email_from", "")
        email_subject = state.get("email_subject", "")
        email_body = state.get("email_body", "")
        email_type = state.get("email_type", "new")
        
        if not email_from or not email_body:
            logger.error(f"Invalid email data for lead {lead_id}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": "Missing required email data (from or body)",
                "error_node": "ingest_email",
            }
        
        # Store in RAG storage
        storage = get_rag_storage()
        storage.store_lead_interaction(
            lead_id=lead_id,
            interaction_type="email_in",
            content=f"Subject: {email_subject}\n\n{email_body}",
            metadata={
                "from": email_from,
                "email_type": email_type,
            },
        )
        
        # Get thread history if this is a reply
        thread_history = ""
        if email_type == "reply":
            thread_history = storage.get_thread_context(lead_id)
        
        logger.info(f"Email ingested for lead {lead_id}, type: {email_type}")
        
        return {
            "status": FlowStatus.UNDERSTANDING,
            "thread_history": thread_history,
            "current_node": "ingest_email",
        }

