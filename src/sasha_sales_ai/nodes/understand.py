"""Lead understanding node"""

import logging
from typing import Any

from ..state import FlowState, FlowStatus, CustomerIntent
from ..chains.lead_analyzer import analyze_lead, check_missing_info
from ..validators import validate_requirements, get_missing_fields_description
from ..utils.langsmith_helpers import get_tracing_context
from ..utils.state_logger import log_state_before, log_state_after

logger = logging.getLogger("sasha_sales_ai.nodes.understand")


def understand_lead(state: FlowState) -> dict[str, Any]:
    """Analyze the lead email and extract requirements.
    
    This node:
    1. Uses the lead analyzer chain to extract structured data
    2. Validates the extracted requirements against required fields
    3. Checks for conditional requirements (logo details if customization requested)
    4. Identifies ALL missing information needed for a complete quote
    5. Determines customer intent for replies
    
    REQUIRED fields for ALL orders:
    - Product type, Quantity, Delivery address, Material preference
    
    CONDITIONAL fields (if customization requested):
    - Logo description, Logo colors, Logo placement, Size distribution
    
    Args:
        state: Current flow state
    
    Returns:
        Updated state fields
    """
    lead_id = state.get("lead_id", "unknown")
    email_type = state.get("email_type", "new")
    
    # Log state before execution
    log_state_before("understand_lead", state)
    
    with get_tracing_context(
        name="understand_lead",
        tags=["node", "understand", lead_id],
        metadata={"lead_id": lead_id, "email_type": email_type},
    ):
        logger.info(f"Understanding lead {lead_id} (type: {email_type})")
        
        try:
            # For replies, pass through to process_reply node (avoids duplicate LLM calls)
            # process_reply will handle intent classification and info extraction
            if email_type == "reply":
                logger.info(f"Reply detected for {lead_id} - deferring to process_reply node")
                
                result = {
                    "status": FlowStatus.UNDERSTANDING,
                    "current_node": "understand_lead",
                }
                
                log_state_after("understand_lead", state, result)
                return result
            
            # For new emails, extract full requirements
            analysis_result = analyze_lead(
                email_from=state.get("email_from", ""),
                email_subject=state.get("email_subject", ""),
                email_body=state.get("email_body", ""),
                thread_history=state.get("thread_history", ""),
            )
            
            # Check if customization was requested
            has_customization = analysis_result.get("has_customization_request", False)
            
            # Also check by looking for keywords in the requirements
            if not has_customization:
                customizations = analysis_result.get("requirements", {}).get("customizations", "")
                if customizations:
                    custom_keywords = ["logo", "print", "design", "custom", "embroid", "screen"]
                    has_customization = any(kw in str(customizations).lower() for kw in custom_keywords)
            
            # Validate extracted requirements with basic validator
            is_valid, basic_missing = validate_requirements(analysis_result)
            
            # Get enhanced missing info check
            requirements_obj = analysis_result.get("requirements", analysis_result)
            try:
                missing_info_result = check_missing_info(
                    requirements=requirements_obj,
                    has_customization=has_customization,
                )
                enhanced_missing = missing_info_result.get("missing_fields", [])
            except Exception as e:
                logger.warning(f"Enhanced missing info check failed: {e}")
                enhanced_missing = []
            
            # Combine missing fields from both sources
            missing_fields = analysis_result.get("missing_fields", [])
            
            # Add basic validation missing fields
            for field in basic_missing:
                if field not in missing_fields:
                    missing_fields.append(field)
            
            # Add enhanced missing fields (which include descriptions)
            for item in enhanced_missing:
                if isinstance(item, dict):
                    field_name = item.get("field", "")
                    if field_name and field_name not in [f.get("field") if isinstance(f, dict) else f for f in missing_fields]:
                        missing_fields.append(item)
                elif item not in missing_fields:
                    missing_fields.append(item)
            
            customer_intent = analysis_result.get("customer_intent", CustomerIntent.NEW_INQUIRY)
            
            logger.info(
                f"Lead {lead_id} analyzed: intent={customer_intent}, "
                f"has_customization={has_customization}, "
                f"missing_count={len(missing_fields)}"
            )
            
            # Get human-readable descriptions for any string-only fields
            missing_descriptions = []
            for field in missing_fields:
                if isinstance(field, dict):
                    missing_descriptions.append(field)
                else:
                    # Get description for simple field name
                    desc = get_missing_fields_description([field])
                    if desc:
                        missing_descriptions.append({
                            "field": field, 
                            "description": desc[0] if desc else f"Please provide {field}"
                        })
                    else:
                        missing_descriptions.append({
                            "field": field,
                            "description": f"Please provide {field}"
                        })
            
            # Flatten requirements - analysis_result contains nested "requirements" object
            # We need to merge the nested requirements to the top level
            flattened_requirements = dict(analysis_result)
            nested_req = analysis_result.get("requirements", {})
            if isinstance(nested_req, dict):
                # Merge nested requirements to top level
                for key, value in nested_req.items():
                    if value is not None:
                        flattened_requirements[key] = value
            
            result = {
                "requirements": flattened_requirements,
                "missing_fields": missing_descriptions,
                "has_customization_request": has_customization,
                "customer_intent": customer_intent,
                "status": FlowStatus.UNDERSTANDING,
                "current_node": "understand_lead",
            }
            
            log_state_after("understand_lead", state, result)
            return result
            
        except Exception as e:
            logger.error(f"Error understanding lead {lead_id}: {e}")
            result = {
                "status": FlowStatus.ERROR,
                "error_message": str(e),
                "error_node": "understand_lead",
            }
            log_state_after("understand_lead", state, result)
            return result
