"""LangGraph StateGraph definition for sales workflow"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import FlowState, FlowStatus, CustomerIntent
from .nodes import (
    ingest_email,
    understand_lead,
    request_clarification,
    check_feasibility,
    calculate_pricing,
    check_approval,
    request_approval,
    send_quote,
    process_reply,
    place_order,
    send_confirmation,
    handle_rejection,
)

logger = logging.getLogger("sasha_sales_ai.graph")


def route_after_understanding(
    state: FlowState,
) -> Literal["process_reply", "request_clarification", "check_feasibility"]:
    """Route after understanding the lead.
    
    Determines the next step based on:
    - Email type (new vs reply)
    - Missing information
    - Customer intent
    
    Args:
        state: Current flow state
    
    Returns:
        Next node name
    """
    email_type = state.get("email_type", "new")
    missing_fields = state.get("missing_fields", [])
    customer_intent = state.get("customer_intent", "")
    
    # If it's a reply, process it
    if email_type == "reply":
        return "process_reply"
    
    # If information is missing, request clarification
    if missing_fields:
        return "request_clarification"
    
    # Otherwise, check feasibility
    return "check_feasibility"


def route_after_feasibility(
    state: FlowState,
) -> Literal["calculate_pricing", "handle_rejection"]:
    """Route after feasibility check.
    
    Args:
        state: Current flow state
    
    Returns:
        Next node name
    """
    is_feasible = state.get("is_feasible", False)
    
    if is_feasible:
        return "calculate_pricing"
    return "handle_rejection"


def route_after_approval_check(
    state: FlowState,
) -> Literal["request_approval", "send_quote"]:
    """Route after checking if approval is needed.
    
    Args:
        state: Current flow state
    
    Returns:
        Next node name
    """
    needs_approval = state.get("needs_approval", False)
    
    if needs_approval:
        return "request_approval"
    return "send_quote"


def route_after_approval_decision(
    state: FlowState,
) -> Literal["send_quote", "handle_rejection"]:
    """Route after approval decision is made.
    
    Args:
        state: Current flow state
    
    Returns:
        Next node name
    """
    approved = state.get("approved")
    
    if approved is True:
        return "send_quote"
    return "handle_rejection"


def route_after_reply(
    state: FlowState,
) -> Literal["place_order", "handle_rejection", "check_feasibility", "request_clarification"]:
    """Route after processing customer reply.
    
    Args:
        state: Current flow state
    
    Returns:
        Next node name
    """
    customer_intent = state.get("customer_intent", "")
    
    if customer_intent == CustomerIntent.CONFIRMATION:
        return "place_order"
    elif customer_intent == CustomerIntent.REJECTION:
        return "handle_rejection"
    elif customer_intent == CustomerIntent.MODIFICATION:
        return "check_feasibility"
    else:  # question, clarification, or unknown
        return "request_clarification"


def should_end(state: FlowState) -> bool:
    """Check if the flow should end.
    
    Args:
        state: Current flow state
    
    Returns:
        True if flow should end
    """
    status = state.get("status", "")
    return status in [
        FlowStatus.COMPLETED,
        FlowStatus.REJECTED,
        FlowStatus.ERROR,
        FlowStatus.CLARIFYING,  # Waiting for reply
        FlowStatus.QUOTE_SENT,  # Waiting for reply
        FlowStatus.APPROVAL_PENDING,  # Waiting for approval
    ]


def create_sales_graph(checkpointer=None):
    """Create the sales workflow graph.
    
    Args:
        checkpointer: Optional checkpointer for state persistence
    
    Returns:
        Compiled LangGraph
    """
    logger.info("Creating sales workflow graph")
    
    # Create the graph with FlowState
    graph = StateGraph(FlowState)
    
    # Add all nodes
    graph.add_node("ingest_email", ingest_email)
    graph.add_node("understand_lead", understand_lead)
    graph.add_node("request_clarification", request_clarification)
    graph.add_node("check_feasibility", check_feasibility)
    graph.add_node("calculate_pricing", calculate_pricing)
    graph.add_node("check_approval", check_approval)
    graph.add_node("request_approval", request_approval)
    graph.add_node("send_quote", send_quote)
    graph.add_node("process_reply", process_reply)
    graph.add_node("place_order", place_order)
    graph.add_node("send_confirmation", send_confirmation)
    graph.add_node("handle_rejection", handle_rejection)
    
    # Entry point
    graph.add_edge(START, "ingest_email")
    graph.add_edge("ingest_email", "understand_lead")
    
    # Conditional routing after understanding
    graph.add_conditional_edges(
        "understand_lead",
        route_after_understanding,
        {
            "process_reply": "process_reply",
            "request_clarification": "request_clarification",
            "check_feasibility": "check_feasibility",
        },
    )
    
    # Clarification ends (waiting for reply)
    graph.add_edge("request_clarification", END)
    
    # Feasibility routing
    graph.add_conditional_edges(
        "check_feasibility",
        route_after_feasibility,
        {
            "calculate_pricing": "calculate_pricing",
            "handle_rejection": "handle_rejection",
        },
    )
    
    # Pricing to approval check
    graph.add_edge("calculate_pricing", "check_approval")
    
    # Approval check routing
    graph.add_conditional_edges(
        "check_approval",
        route_after_approval_check,
        {
            "request_approval": "request_approval",
            "send_quote": "send_quote",
        },
    )
    
    # Request approval ends (waiting for approval - interrupt point)
    graph.add_edge("request_approval", END)
    
    # Quote sent ends (waiting for customer reply)
    graph.add_edge("send_quote", END)
    
    # Reply processing routing
    graph.add_conditional_edges(
        "process_reply",
        route_after_reply,
        {
            "place_order": "place_order",
            "handle_rejection": "handle_rejection",
            "check_feasibility": "check_feasibility",
            "request_clarification": "request_clarification",
        },
    )
    
    # Order to confirmation
    graph.add_edge("place_order", "send_confirmation")
    
    # Terminal nodes
    graph.add_edge("send_confirmation", END)
    graph.add_edge("handle_rejection", END)
    
    # Use default memory checkpointer if none provided
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    # Compile with checkpointer and interrupt points
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["request_approval"],  # Interrupt before approval
    )
    
    logger.info("Sales workflow graph created successfully")
    
    return compiled


def create_reply_entry_graph(checkpointer=None):
    """Create a graph specifically for processing replies.
    
    This graph starts at process_reply instead of ingest_email.
    
    Args:
        checkpointer: Optional checkpointer for state persistence
    
    Returns:
        Compiled LangGraph for reply processing
    """
    logger.info("Creating reply processing graph")
    
    graph = StateGraph(FlowState)
    
    # Add nodes needed for reply processing
    graph.add_node("ingest_email", ingest_email)
    graph.add_node("process_reply", process_reply)
    graph.add_node("request_clarification", request_clarification)
    graph.add_node("check_feasibility", check_feasibility)
    graph.add_node("calculate_pricing", calculate_pricing)
    graph.add_node("check_approval", check_approval)
    graph.add_node("request_approval", request_approval)
    graph.add_node("send_quote", send_quote)
    graph.add_node("place_order", place_order)
    graph.add_node("send_confirmation", send_confirmation)
    graph.add_node("handle_rejection", handle_rejection)
    
    # Entry through ingest (which will detect it's a reply)
    graph.add_edge(START, "ingest_email")
    graph.add_edge("ingest_email", "process_reply")
    
    # Reply processing routing
    graph.add_conditional_edges(
        "process_reply",
        route_after_reply,
        {
            "place_order": "place_order",
            "handle_rejection": "handle_rejection",
            "check_feasibility": "check_feasibility",
            "request_clarification": "request_clarification",
        },
    )
    
    # Add remaining edges (same as main graph)
    graph.add_edge("request_clarification", END)
    
    graph.add_conditional_edges(
        "check_feasibility",
        route_after_feasibility,
        {
            "calculate_pricing": "calculate_pricing",
            "handle_rejection": "handle_rejection",
        },
    )
    
    graph.add_edge("calculate_pricing", "check_approval")
    
    graph.add_conditional_edges(
        "check_approval",
        route_after_approval_check,
        {
            "request_approval": "request_approval",
            "send_quote": "send_quote",
        },
    )
    
    graph.add_edge("request_approval", END)
    graph.add_edge("send_quote", END)
    graph.add_edge("place_order", "send_confirmation")
    graph.add_edge("send_confirmation", END)
    graph.add_edge("handle_rejection", END)
    
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["request_approval"],
    )
    
    logger.info("Reply processing graph created successfully")
    
    return compiled

