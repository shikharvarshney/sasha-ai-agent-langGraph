"""Reply processing node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus, CustomerIntent
from ..chains.lead_analyzer import classify_reply_intent
from ..utils.langsmith_helpers import get_tracing_context

logger = logging.getLogger("sasha_sales_ai.nodes.reply")


def process_reply(state: FlowState) -> dict[str, Any]:
    """Process a customer reply email.
    
    This node:
    1. Classifies the customer's intent from their reply
    2. Extracts key information from the reply
    3. Determines next steps based on intent
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields with intent classification
    """
    lead_id = state.get("lead_id", "unknown")
    
    with get_tracing_context(
        name="process_reply",
        tags=["node", "reply", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Processing reply for lead {lead_id}")
        
        try:
            email_body = state.get("email_body", "")
            thread_history = state.get("thread_history", "")
            
            # Classify the reply intent
            intent_result = classify_reply_intent(
                email_body=email_body,
                thread_history=thread_history,
            )
            
            customer_intent = intent_result.get("intent", CustomerIntent.QUESTION)
            confidence = intent_result.get("confidence", 0)
            key_points = intent_result.get("key_points", [])
            action_required = intent_result.get("action_required", "")
            
            logger.info(
                f"Reply intent for {lead_id}: {customer_intent} "
                f"(confidence: {confidence})"
            )
            
            # Update requirements with any new information from the reply
            current_requirements = state.get("requirements", {})
            current_requirements["reply_key_points"] = key_points
            current_requirements["action_required"] = action_required
            
            # Determine customer confirmation status
            customer_confirmed = customer_intent == CustomerIntent.CONFIRMATION
            
            return {
                "customer_intent": customer_intent,
                "customer_confirmed": customer_confirmed,
                "requirements": current_requirements,
                "status": FlowStatus.UNDERSTANDING,
                "current_node": "process_reply",
            }
            
        except Exception as e:
            logger.error(f"Error processing reply for {lead_id}: {e}")
            return {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "process_reply",
            }

