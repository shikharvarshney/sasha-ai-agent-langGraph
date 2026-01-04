"""Reply processing node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus, CustomerIntent
from ..chains.lead_analyzer import classify_reply_intent
from ..utils.langsmith_helpers import get_tracing_context
from ..utils.state_logger import log_state_before, log_state_after, log_incoming_email

logger = logging.getLogger("sasha_sales_ai.nodes.reply")


def process_reply(state: FlowState) -> dict[str, Any]:
    """Process a customer reply email.
    
    This node:
    1. Classifies the customer's intent from their reply
    2. Extracts ALL new information provided in the reply
    3. Determines next steps based on intent
    
    CRITICAL: Distinguishes between:
    - "providing_info": Customer giving missing info (NOT confirmation)
    - "confirmation": Customer explicitly agrees to proceed
    - "rejection": Customer declines
    - "question": Customer has questions
    - "modification": Customer wants changes
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields with intent classification and extracted info
    """
    lead_id = state.get("lead_id", "unknown")
    
    # Log state before execution
    log_state_before("process_reply", state)
    
    # Log the incoming reply email
    log_incoming_email(state)
    
    with get_tracing_context(
        name="process_reply",
        tags=["node", "reply", lead_id],
        metadata={"lead_id": lead_id},
    ):
        logger.info(f"Processing reply for lead {lead_id}")
        
        try:
            email_body = state.get("email_body", "")
            thread_history = state.get("thread_history", "")
            feasibility_checked = state.get("feasibility_checked", False)
            quote_sent = state.get("quote_sent", False)
            
            # Build previous quote context if available
            previous_quote = ""
            if state.get("total_amount"):
                previous_quote = f"Total: ${state.get('total_amount')}"
            if state.get("price_quote"):
                previous_quote = state.get("price_quote", "")
            
            # Classify the reply intent with enhanced prompt
            intent_result = classify_reply_intent(
                email_body=email_body,
                thread_history=thread_history,
                previous_quote=previous_quote,
            )
            
            # Extract classification results
            customer_intent = intent_result.get("intent", CustomerIntent.QUESTION)
            confirmed = intent_result.get("confirmed", False)
            modifications = intent_result.get("modifications", {})
            questions = intent_result.get("questions", [])
            key_points = intent_result.get("key_points", [])
            action_required = intent_result.get("action_required", "")
            summary = intent_result.get("summary", "")
            
            logger.info(
                f"Reply intent for {lead_id}: {customer_intent}, "
                f"confirmed={confirmed}, modifications={bool(modifications)}"
            )
            
            if modifications:
                logger.info(f"Modifications extracted: {list(modifications.keys())}")
            
            # Update requirements with any new information from the reply
            current_requirements = state.get("requirements", {})
            
            # Merge modifications into requirements (only non-null values)
            if modifications:
                for key, value in modifications.items():
                    if value is not None and value != "":
                        # Update the requirements with new info
                        current_requirements[key] = value
                        logger.info(f"Updated requirement '{key}' from reply: {value}")
            
            # Add reply metadata
            current_requirements["reply_key_points"] = key_points
            current_requirements["reply_questions"] = questions
            current_requirements["action_required"] = action_required
            current_requirements["reply_summary"] = summary
            
            # CRITICAL: Only set customer_confirmed to True if:
            # 1. Intent is explicitly "confirmation" AND
            # 2. The confirmed flag is True
            customer_confirmed = (
                customer_intent == CustomerIntent.CONFIRMATION or 
                customer_intent == "confirmation" or
                confirmed is True
            )
            
            # If customer is providing info, update missing_fields
            missing_fields = state.get("missing_fields", [])
            if customer_intent == "providing_info" and modifications:
                # Remove fields that were just provided
                for key in modifications.keys():
                    if modifications[key]:
                        missing_fields = [
                            f for f in missing_fields 
                            if key.lower() not in str(f).lower() 
                            and str(f).lower() not in key.lower()
                        ]
            
            result = {
                "customer_intent": customer_intent,
                "customer_confirmed": customer_confirmed,
                "requirements": current_requirements,
                "missing_fields": missing_fields,
                "status": FlowStatus.UNDERSTANDING,
                "current_node": "process_reply",
            }
            
            log_state_after("process_reply", state, result)
            return result
            
        except Exception as e:
            logger.error(f"Error processing reply for {lead_id}: {e}")
            result = {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "process_reply",
            }
            log_state_after("process_reply", state, result)
            return result
