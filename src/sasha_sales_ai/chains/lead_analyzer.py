"""Lead analysis chain using LangChain LCEL"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

from ..config import get_settings

logger = logging.getLogger("sasha_sales_ai.chains.lead_analyzer")

LEAD_ANALYZER_SYSTEM_PROMPT = """You are an expert sales lead analyzer for a promotional products company.
You are METICULOUS and NEVER miss important details.

Your job is to analyze incoming customer emails and extract ALL requirements.

REQUIRED FIELDS for ALL orders:
- Product type (t-shirt, polo, hoodie, cap, mug, tote bag, jacket)
- Quantity (exact number of items)
- Delivery address (full shipping address)
- Material preference (cotton, polyester, blend, etc.)

CONDITIONAL FIELDS (required if customization is mentioned):
- If customer mentions "logo", "print", "design", "custom", or "branding":
  * logo_description: Logo/design description or image reference - REQUIRED
  * logo_color: Logo color(s) - REQUIRED  
  * logo_placement: Logo placement (front, back, sleeve, pocket) - REQUIRED
- If order has multiple sizes:
  * size_distribution: Size breakdown (e.g., 10 S, 20 M, 50 L, 20 XL) - REQUIRED

IMPORTANT: 
- If ANY required field is missing, add it to missing_fields
- If customer mentions customization but doesn't provide logo details, those are MISSING
- Never assume or guess missing information
- Be very thorough - you are the first line of defense against incomplete orders

Return your analysis as JSON with this EXACT structure:
{{
    "email_type": "new or reply",
    "customer_name": "extracted name or null",
    "company_name": "company name or null",
    "requirements": {{
        "product_type": "t-shirt, polo, hoodie, cap, mug, tote_bag, jacket, or null",
        "quantity": "number or null",
        "timeline": "delivery timeline mentioned or null",
        "delivery_address": "full address or null",
        "material": "cotton, polyester, blend, or null",
        "customizations": "description of requested customizations or null",
        "logo_description": "logo details or null",
        "logo_color": "logo colors or null",
        "logo_placement": "front, back, sleeve, pocket, or null",
        "size_distribution": "size breakdown object or null"
    }},
    "missing_fields": ["list of ALL missing required and conditional fields"],
    "has_customization_request": "true if logo/print/design mentioned, false otherwise",
    "customer_intent": "new_inquiry, clarification, confirmation, rejection, modification, or question",
    "confidence_score": "0-1 confidence in extraction",
    "summary": "brief summary of the request"
}}"""

LEAD_ANALYZER_HUMAN_TEMPLATE = """Analyze the following email:

From: {email_from}
Subject: {email_subject}

Body:
{email_body}

{thread_context}

Extract ALL information and identify what's missing. Be thorough!
Return your analysis as JSON."""


def create_lead_analyzer_chain():
    """Create the lead analyzer chain using LCEL.
    
    Returns:
        Runnable chain for lead analysis
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=settings.temperature,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", LEAD_ANALYZER_SYSTEM_PROMPT),
        ("human", LEAD_ANALYZER_HUMAN_TEMPLATE),
    ])
    
    parser = JsonOutputParser()
    
    # Build the chain with LCEL
    chain = (
        RunnablePassthrough.assign(
            thread_context=lambda x: f"\nPrevious conversation:\n{x.get('thread_history', '')}" 
            if x.get('thread_history') else ""
        )
        | prompt
        | llm
        | parser
    )
    
    return chain


def analyze_lead(
    email_from: str,
    email_subject: str,
    email_body: str,
    thread_history: str = "",
) -> dict[str, Any]:
    """Analyze a lead email and extract requirements.
    
    Args:
        email_from: Sender email address
        email_subject: Email subject line
        email_body: Email body content
        thread_history: Optional previous conversation history
    
    Returns:
        Dictionary with extracted requirements
    """
    logger.info(f"Analyzing lead from {email_from}")
    
    chain = create_lead_analyzer_chain()
    
    result = chain.invoke({
        "email_from": email_from,
        "email_subject": email_subject,
        "email_body": email_body,
        "thread_history": thread_history,
    })
    
    logger.info(f"Lead analysis complete: intent={result.get('customer_intent')}, missing={result.get('missing_fields')}")
    
    return result


# Missing info checker - determines if we can proceed or need clarification
MISSING_INFO_CHECKER_PROMPT = """Review the extracted requirements and determine what information is STILL missing.

Requirements extracted so far:
{requirements}

Has customization been requested: {has_customization}

REQUIRED fields for ALL orders:
- Product type (t-shirt, polo, hoodie, cap, mug, tote bag, jacket)
- Quantity (number of items)
- Delivery address (for shipping)
- Material preference (cotton, polyester, blend, etc.)

CONDITIONAL fields (REQUIRED if customization is requested):
- If logo/print is requested (has_customization = true):
  * logo_description: Logo/design description or image reference
  * logo_color: Logo color(s)
  * logo_placement: Logo placement (front, back, sleeve, pocket, etc.)
- If multiple sizes are needed:
  * size_distribution: Size breakdown (e.g., {{"S": 10, "M": 20, "L": 50, "XL": 20}})

IMPORTANT: 
- If has_customization is true and logo details are missing, they MUST be in missing_fields
- Only list fields that are ACTUALLY missing (null or empty)
- Be specific about what's needed

Return JSON:
{{
    "has_missing_info": true/false,
    "missing_fields": [
        {{"field": "field_name", "description": "Clear description of what's needed"}}
    ],
    "can_proceed_to_pricing": true/false
}}"""


def create_missing_info_checker_chain():
    """Create a chain to check for missing information.
    
    Returns:
        Runnable chain for missing info check
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("human", MISSING_INFO_CHECKER_PROMPT),
    ])
    
    parser = JsonOutputParser()
    
    return prompt | llm | parser


def check_missing_info(requirements: dict, has_customization: bool = False) -> dict[str, Any]:
    """Check what information is still missing from requirements.
    
    Args:
        requirements: Extracted requirements dict
        has_customization: Whether customization was requested
    
    Returns:
        Dictionary with missing info details
    """
    logger.info("Checking for missing information")
    
    chain = create_missing_info_checker_chain()
    
    import json
    result = chain.invoke({
        "requirements": json.dumps(requirements, indent=2),
        "has_customization": str(has_customization).lower(),
    })
    
    logger.info(f"Missing info check: has_missing={result.get('has_missing_info')}")
    
    return result


# Intent classification chain for reply processing
INTENT_CLASSIFIER_PROMPT = """Analyze the customer's reply to determine their intent and extract ANY new information.

Previous context:
{thread_history}

Previous quote (if any):
{previous_quote}

Customer reply:
{email_body}

CRITICAL DISTINCTION:
- "providing_info" = Customer is providing missing information (address, sizes, material, logo details, etc.)
- "confirmation" = Customer EXPLICITLY says "yes", "I confirm", "proceed with order", "accept the quote"
- "rejection" = Customer says "no", "cancel", "not interested"
- "question" = Customer is asking questions about the product/quote
- "modification" = Customer wants to change previously confirmed details

IMPORTANT: 
- If customer provides information like address, sizes, material - that is "providing_info", NOT "confirmation"!
- "confirmation" should ONLY be true if customer explicitly agrees to proceed with an order/quote
- Extract ALL new information provided into the modifications object

Return JSON:
{{
    "intent": "providing_info, confirmation, rejection, question, or modification",
    "confirmed": true/false (TRUE only if customer explicitly confirms order/quote),
    "modifications": {{
        "delivery_address": "any address mentioned or null",
        "material": "any material preference or null",
        "size_distribution": "any size breakdown or null",
        "logo_description": "any logo/design details or null",
        "logo_color": "any logo colors or null",
        "logo_placement": "any placement info or null",
        "quantity": "if quantity changed or null",
        "timeline": "if timeline mentioned or null"
    }},
    "questions": ["list of questions if any"],
    "key_points": ["list of key points from the reply"],
    "summary": "brief summary of what customer is saying",
    "action_required": "what action should be taken next"
}}

DO NOT leave modifications as all nulls if the customer provided ANY new information!"""


def create_intent_classifier_chain():
    """Create an intent classification chain for reply processing.
    
    Returns:
        Runnable chain for intent classification
    """
    settings = get_settings()
    
    llm = ChatOpenAI(
        model=settings.model_name,
        temperature=0,
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("human", INTENT_CLASSIFIER_PROMPT),
    ])
    
    parser = JsonOutputParser()
    
    return prompt | llm | parser


def classify_reply_intent(
    email_body: str,
    thread_history: str = "",
    previous_quote: str = "",
) -> dict[str, Any]:
    """Classify the intent of a customer reply and extract new information.
    
    Args:
        email_body: Reply email body
        thread_history: Previous conversation history
        previous_quote: Previous quote if any
    
    Returns:
        Dictionary with intent classification and extracted info
    """
    logger.info("Classifying reply intent")
    
    chain = create_intent_classifier_chain()
    
    result = chain.invoke({
        "email_body": email_body,
        "thread_history": thread_history,
        "previous_quote": previous_quote or "No previous quote",
    })
    
    logger.info(f"Intent classified: {result.get('intent')}, confirmed={result.get('confirmed')}")
    
    return result
