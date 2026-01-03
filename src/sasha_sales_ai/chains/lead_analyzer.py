"""Lead analysis chain using LangChain LCEL"""

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

from ..config import get_settings

logger = logging.getLogger("sasha_sales_ai.chains.lead_analyzer")

LEAD_ANALYZER_SYSTEM_PROMPT = """You are an expert sales lead analyzer. Your job is to extract structured information from customer emails and classify their intent.

Analyze the email and extract the following information in JSON format:
{{
    "customer_name": "extracted customer name or null if not found",
    "company_name": "extracted company name or null if not found",
    "product_type": "one of: widget, gadget, component, assembly, or null if unclear",
    "quantity": "number of units requested or null if not specified",
    "timeline": "delivery timeline mentioned or null if not specified",
    "customizations": "any customizations requested or null",
    "material": "material preference if mentioned or null",
    "budget": "budget mentioned or null",
    "customer_intent": "one of: new_inquiry, clarification, confirmation, rejection, modification, question",
    "confidence_score": "0-1 confidence in the extraction",
    "summary": "brief summary of the request"
}}

Be precise and only extract information that is explicitly stated or can be reasonably inferred.
If information is ambiguous, use null and note it in the summary.
"""

LEAD_ANALYZER_HUMAN_TEMPLATE = """Analyze the following email:

From: {email_from}
Subject: {email_subject}

Body:
{email_body}

{thread_context}

Extract the structured information and return as JSON."""


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
    
    logger.info(f"Lead analysis complete: intent={result.get('customer_intent')}")
    
    return result


# Intent classification chain for reply processing
INTENT_CLASSIFIER_PROMPT = """Classify the customer's intent from their reply email.

Previous context:
{thread_history}

Customer reply:
{email_body}

Classify the intent as one of:
- confirmation: Customer is confirming/accepting a quote or order
- rejection: Customer is declining or not interested
- modification: Customer wants changes to the quote
- question: Customer has questions about the quote/product
- clarification: Customer is providing requested information

Return JSON:
{{
    "intent": "one of the above",
    "confidence": "0-1 confidence score",
    "key_points": ["list of key points from the reply"],
    "action_required": "brief description of what action is needed"
}}"""


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
) -> dict[str, Any]:
    """Classify the intent of a customer reply.
    
    Args:
        email_body: Reply email body
        thread_history: Previous conversation history
    
    Returns:
        Dictionary with intent classification
    """
    logger.info("Classifying reply intent")
    
    chain = create_intent_classifier_chain()
    
    result = chain.invoke({
        "email_body": email_body,
        "thread_history": thread_history,
    })
    
    logger.info(f"Intent classified: {result.get('intent')}")
    
    return result

