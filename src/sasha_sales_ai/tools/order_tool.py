"""Order management tool"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Any
from langchain_core.tools import tool

logger = logging.getLogger("sasha_sales_ai.tools.order")

# In-memory order storage (would be a database in production)
_orders: dict[str, dict[str, Any]] = {}


@tool
def create_order(
    lead_id: str,
    customer_email: str,
    product_type: str,
    quantity: int,
    total_amount: float,
    customizations: Optional[str] = None,
    timeline_days: Optional[int] = None,
    notes: Optional[str] = None,
) -> str:
    """Create a new order in the system.
    
    Args:
        lead_id: The lead ID associated with this order
        customer_email: Customer's email address
        product_type: Type of product ordered
        quantity: Number of units
        total_amount: Total order amount
        customizations: Optional customization details
        timeline_days: Delivery timeline in days
        notes: Optional order notes
    
    Returns:
        JSON string with order details including order ID
    """
    import json
    
    logger.info(f"Creating order for lead {lead_id}")
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    # Calculate estimated delivery
    production_days = timeline_days or 14
    estimated_delivery = datetime.now() + timedelta(days=production_days)
    
    order = {
        "order_id": order_id,
        "lead_id": lead_id,
        "customer_email": customer_email,
        "product_type": product_type,
        "quantity": quantity,
        "total_amount": total_amount,
        "customizations": customizations,
        "timeline_days": production_days,
        "notes": notes,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
        "estimated_delivery": estimated_delivery.strftime("%Y-%m-%d"),
    }
    
    _orders[order_id] = order
    
    logger.info(f"Order created: {order_id}")
    
    return json.dumps(order)


@tool
def get_order(order_id: str) -> str:
    """Get order details by order ID.
    
    Args:
        order_id: The order ID to look up
    
    Returns:
        JSON string with order details or error message
    """
    import json
    
    if order_id not in _orders:
        return json.dumps({"error": f"Order {order_id} not found"})
    
    return json.dumps(_orders[order_id])


@tool
def update_order_status(order_id: str, new_status: str, notes: Optional[str] = None) -> str:
    """Update the status of an order.
    
    Args:
        order_id: The order ID to update
        new_status: New status (confirmed, processing, shipped, delivered, cancelled)
        notes: Optional status update notes
    
    Returns:
        JSON string with updated order or error message
    """
    import json
    
    valid_statuses = ["confirmed", "processing", "shipped", "delivered", "cancelled"]
    
    if new_status not in valid_statuses:
        return json.dumps({
            "error": f"Invalid status: {new_status}",
            "valid_statuses": valid_statuses,
        })
    
    if order_id not in _orders:
        return json.dumps({"error": f"Order {order_id} not found"})
    
    _orders[order_id]["status"] = new_status
    _orders[order_id]["updated_at"] = datetime.now().isoformat()
    
    if notes:
        _orders[order_id]["status_notes"] = notes
    
    logger.info(f"Order {order_id} status updated to {new_status}")
    
    return json.dumps(_orders[order_id])


@tool
def cancel_order(order_id: str, reason: str) -> str:
    """Cancel an order.
    
    Args:
        order_id: The order ID to cancel
        reason: Reason for cancellation
    
    Returns:
        JSON string with cancellation confirmation or error
    """
    import json
    
    if order_id not in _orders:
        return json.dumps({"error": f"Order {order_id} not found"})
    
    order = _orders[order_id]
    
    if order["status"] in ["shipped", "delivered"]:
        return json.dumps({
            "error": f"Cannot cancel order {order_id} - already {order['status']}"
        })
    
    order["status"] = "cancelled"
    order["cancellation_reason"] = reason
    order["cancelled_at"] = datetime.now().isoformat()
    
    logger.info(f"Order {order_id} cancelled: {reason}")
    
    return json.dumps({
        "message": f"Order {order_id} has been cancelled",
        "order": order,
    })


@tool
def get_orders_by_lead(lead_id: str) -> str:
    """Get all orders for a specific lead.
    
    Args:
        lead_id: The lead ID to search for
    
    Returns:
        JSON string with list of orders
    """
    import json
    
    lead_orders = [
        order for order in _orders.values()
        if order["lead_id"] == lead_id
    ]
    
    return json.dumps({"lead_id": lead_id, "orders": lead_orders})


def format_order_details(order_data: dict) -> str:
    """Format order data into a human-readable string.
    
    Args:
        order_data: Order dictionary
    
    Returns:
        Formatted order details string
    """
    return f"""
Product: {order_data.get('product_type', 'N/A').title()}
Quantity: {order_data.get('quantity', 0):,} units
Customizations: {order_data.get('customizations', 'None')}
Total Amount: ${order_data.get('total_amount', 0):,.2f}
""".strip()

