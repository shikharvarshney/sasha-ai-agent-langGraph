"""Deterministic requirement validation"""

import re
import logging
from typing import Any

logger = logging.getLogger("sasha_sales_ai.validators")

# Required fields for a complete order request
REQUIRED_FIELDS = [
    "product_type",
    "quantity",
]

# Optional but helpful fields
HELPFUL_FIELDS = [
    "timeline",
    "customizations",
    "material",
    "budget",
]


def validate_requirements(requirements: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate that all required information is present.
    
    Args:
        requirements: Dictionary of extracted requirements
    
    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing_fields = []
    
    for field in REQUIRED_FIELDS:
        value = requirements.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_fields.append(field)
    
    # Check quantity is a valid number
    quantity = requirements.get("quantity")
    if quantity is not None:
        try:
            qty = int(quantity) if isinstance(quantity, str) else quantity
            if qty <= 0:
                missing_fields.append("quantity (must be positive)")
        except (ValueError, TypeError):
            missing_fields.append("quantity (must be a number)")
    
    is_valid = len(missing_fields) == 0
    
    logger.info(f"Validation result: valid={is_valid}, missing={missing_fields}")
    
    return is_valid, missing_fields


def validate_email_address(email: str) -> bool:
    """Validate that an email address is properly formatted.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_product_type(product_type: str) -> tuple[bool, str]:
    """Validate and normalize product type.
    
    Args:
        product_type: Product type string
    
    Returns:
        Tuple of (is_valid, normalized_type)
    """
    valid_types = {"widget", "gadget", "component", "assembly"}
    
    normalized = product_type.lower().strip()
    
    # Handle common variations
    type_aliases = {
        "widgets": "widget",
        "gadgets": "gadget",
        "components": "component",
        "assemblies": "assembly",
        "part": "component",
        "parts": "component",
        "unit": "widget",
        "units": "widget",
    }
    
    if normalized in type_aliases:
        normalized = type_aliases[normalized]
    
    is_valid = normalized in valid_types
    
    return is_valid, normalized


def validate_quantity(quantity: Any) -> tuple[bool, int, str]:
    """Validate and parse quantity.
    
    Args:
        quantity: Quantity value (string or number)
    
    Returns:
        Tuple of (is_valid, parsed_quantity, error_message)
    """
    try:
        if isinstance(quantity, str):
            # Remove commas and whitespace
            clean = quantity.replace(",", "").strip()
            qty = int(clean)
        else:
            qty = int(quantity)
        
        if qty <= 0:
            return False, 0, "Quantity must be positive"
        
        if qty > 100000:
            return False, 0, "Quantity exceeds maximum order size (100,000)"
        
        return True, qty, ""
    
    except (ValueError, TypeError) as e:
        return False, 0, f"Invalid quantity format: {e}"


def validate_timeline(timeline_days: Any) -> tuple[bool, int, str]:
    """Validate delivery timeline.
    
    Args:
        timeline_days: Timeline in days
    
    Returns:
        Tuple of (is_valid, parsed_days, error_message)
    """
    try:
        if isinstance(timeline_days, str):
            # Try to extract number from string like "2 weeks" or "14 days"
            numbers = re.findall(r'\d+', timeline_days)
            if not numbers:
                return False, 0, "Could not parse timeline"
            
            days = int(numbers[0])
            
            # Handle weeks
            if "week" in timeline_days.lower():
                days *= 7
            # Handle months
            elif "month" in timeline_days.lower():
                days *= 30
        else:
            days = int(timeline_days)
        
        if days < 1:
            return False, 0, "Timeline must be at least 1 day"
        
        if days > 365:
            return False, 0, "Timeline exceeds maximum (365 days)"
        
        return True, days, ""
    
    except (ValueError, TypeError) as e:
        return False, 0, f"Invalid timeline format: {e}"


def extract_quantity_from_text(text: str) -> int | None:
    """Extract quantity from natural language text.
    
    Args:
        text: Text to parse
    
    Returns:
        Extracted quantity or None
    """
    # Common patterns for quantities
    patterns = [
        r'(\d{1,3}(?:,\d{3})*)\s*(?:units?|pieces?|items?|pcs?)',
        r'(?:need|want|order|require)\s*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*(?:of|x)\s*',
        r'quantity[:\s]+(\d{1,3}(?:,\d{3})*)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            qty_str = match.group(1).replace(",", "")
            try:
                return int(qty_str)
            except ValueError:
                continue
    
    return None


def extract_product_type_from_text(text: str) -> str | None:
    """Extract product type from natural language text.
    
    Args:
        text: Text to parse
    
    Returns:
        Extracted product type or None
    """
    text_lower = text.lower()
    
    product_keywords = {
        "widget": ["widget", "widgets"],
        "gadget": ["gadget", "gadgets", "device", "devices"],
        "component": ["component", "components", "part", "parts"],
        "assembly": ["assembly", "assemblies", "kit", "kits"],
    }
    
    for product_type, keywords in product_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return product_type
    
    return None


def get_missing_fields_description(missing_fields: list[str]) -> list[str]:
    """Convert field names to human-readable descriptions.
    
    Args:
        missing_fields: List of missing field names
    
    Returns:
        List of human-readable descriptions
    """
    descriptions = {
        "product_type": "What type of product do you need? (widget, gadget, component, or assembly)",
        "quantity": "How many units do you need?",
        "timeline": "When do you need the order delivered?",
        "customizations": "Do you need any customizations? (logo printing, color matching, etc.)",
        "material": "What material would you prefer?",
        "budget": "What is your budget for this order?",
    }
    
    result = []
    for field in missing_fields:
        # Handle fields with additional info like "quantity (must be positive)"
        base_field = field.split(" (")[0]
        if base_field in descriptions:
            result.append(descriptions[base_field])
        else:
            result.append(f"Please provide: {field}")
    
    return result

