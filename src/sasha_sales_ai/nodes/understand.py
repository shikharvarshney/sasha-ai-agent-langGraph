"""Lead understanding node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus, CustomerIntent
from ..chains.lead_analyzer import analyze_lead, classify_reply_intent
from ..validators import validate_requirements, get_missing_fields_description
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.understand")


def understand_lead(state: FlowState) -> dict[str, Any]:
    """Analyze the lead email and extract requirements.
    
    This node:
    1. Uses the lead analyzer chain to extract structured data
    2. Validates the extracted requirements
    3. Identifies missing information
    4. Determines customer intent for replies
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    email_type = state.get("email_type", "new")
    
    with get_tracing_context(
        name="understand_lead",
        tags=["node", "understand", lead_id],
        metadata={"lead_id": lead_id, "email_type": email_type},
    ):
        logger.info(f"Understanding lead {lead_id}")
        
        try:
            # For replies, classify intent first
            if email_type == "reply":
                intent_result = classify_reply_intent(
                    email_body=state.get("email_body", ""),
                    thread_history=state.get("thread_history", ""),
                )
                customer_intent = intent_result.get("intent", CustomerIntent.QUESTION)
                
                logger.info(f"Reply intent for {lead_id}: {customer_intent}")
                
                return {
                    "customer_intent": customer_intent,
                    "requirements": intent_result,
                    "status": FlowStatus.UNDERSTANDING,
                    "current_node": "understand_lead",
                }
            
            # For new emails, extract full requirements
            analysis_result = analyze_lead(
                email_from=state.get("email_from", ""),
                email_subject=state.get("email_subject", ""),
                email_body=state.get("email_body", ""),
                thread_history=state.get("thread_history", ""),
            )
            
            # Validate extracted requirements
            is_valid, missing_fields = validate_requirements(analysis_result)
            
            customer_intent = analysis_result.get("customer_intent", CustomerIntent.NEW_INQUIRY)
            
            logger.info(
                f"Lead {lead_id} analyzed: valid={is_valid}, "
                f"intent={customer_intent}, missing={missing_fields}"
            )
            
            # Get human-readable descriptions of missing fields
            missing_descriptions = get_missing_fields_description(missing_fields)
            
            return {
                "requirements": analysis_result,
                "missing_fields": missing_descriptions,
                "customer_intent": customer_intent,
                "status": FlowStatus.UNDERSTANDING,
                "current_node": "understand_lead",
            }
            
        except Exception as e:
            logger.error(f"Error understanding lead {lead_id}: {e}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "understand_lead",
            }

