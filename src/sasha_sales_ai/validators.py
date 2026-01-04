"""Deterministic requirement validation"""

import re
import logging
from typing import Any

logger = logging.getLogger("sasha_sales_ai.validators")

# Required fields for ALL orders
REQUIRED_FIELDS = [
    "product_type",
    "quantity",
    "delivery_address",
    "material",
]

# Conditional fields - required if customization is requested
CUSTOMIZATION_REQUIRED_FIELDS = [
    "logo_description",
    "logo_color",
    "logo_placement",
]

# Optional but helpful fields
HELPFUL_FIELDS = [
    "timeline",
    "size_distribution",
    "budget",
]

# Valid product types
VALID_PRODUCT_TYPES = {
    "t-shirt", "tshirt", "t shirt",
    "polo", "polo shirt",
    "hoodie", "hooded sweatshirt",
    "cap", "hat", "baseball cap",
    "mug", "coffee mug",
    "tote bag", "tote_bag", "bag",
    "jacket",
}

# Product type normalization mapping
PRODUCT_TYPE_ALIASES = {
    "t-shirt": "t-shirt",
    "tshirt": "t-shirt",
    "t shirt": "t-shirt",
    "polo": "polo",
    "polo shirt": "polo",
    "hoodie": "hoodie",
    "hooded sweatshirt": "hoodie",
    "cap": "cap",
    "hat": "cap",
    "baseball cap": "cap",
    "mug": "mug",
    "coffee mug": "mug",
    "tote bag": "tote_bag",
    "tote_bag": "tote_bag",
    "bag": "tote_bag",
    "jacket": "jacket",
}

# Keywords that indicate customization is requested
CUSTOMIZATION_KEYWORDS = [
    "logo", "print", "printing", "printed",
    "design", "custom", "customiz", "personali",
    "embroid", "screen print", "dtg", "brand",
]


def validate_requirements(requirements: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate that all required information is present.
    
    Args:
        requirements: Dictionary of extracted requirements
    
    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing_fields = []
    
    # Check if requirements is nested
    req_data = requirements.get("requirements", requirements)
    
    # Check basic required fields
    for field in REQUIRED_FIELDS:
        value = req_data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_fields.append(field)
    
    # Check quantity is a valid number
    quantity = req_data.get("quantity")
    if quantity is not None:
        try:
            qty = int(quantity) if isinstance(quantity, str) else quantity
            if qty <= 0:
                if "quantity" not in missing_fields:
                    missing_fields.append("quantity")
        except (ValueError, TypeError):
            if "quantity" not in missing_fields:
                missing_fields.append("quantity")
    
    # Check if customization is requested
    has_customization = check_customization_requested(req_data)
    
    # If customization requested, check for logo details
    if has_customization:
        for field in CUSTOMIZATION_REQUIRED_FIELDS:
            value = req_data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)
    
    is_valid = len(missing_fields) == 0
    
    logger.info(
        f"Validation result: valid={is_valid}, "
        f"has_customization={has_customization}, missing={missing_fields}"
    )
    
    return is_valid, missing_fields


def check_customization_requested(requirements: dict[str, Any]) -> bool:
    """Check if customization was requested in the requirements.
    
    Args:
        requirements: Dictionary of extracted requirements
    
    Returns:
        True if customization is requested
    """
    # Check explicit flag
    if requirements.get("has_customization_request"):
        return True
    
    # Check customizations field
    customizations = str(requirements.get("customizations", "")).lower()
    
    # Check logo-related fields
    logo_desc = str(requirements.get("logo_description", "")).lower()
    logo_color = str(requirements.get("logo_color", "")).lower()
    logo_placement = str(requirements.get("logo_placement", "")).lower()
    
    # Check summary/email body for keywords
    summary = str(requirements.get("summary", "")).lower()
    
    all_text = f"{customizations} {logo_desc} {logo_color} {logo_placement} {summary}"
    
    return any(keyword in all_text for keyword in CUSTOMIZATION_KEYWORDS)


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
    normalized = product_type.lower().strip()
    
    # Try direct match
    if normalized in PRODUCT_TYPE_ALIASES:
        return True, PRODUCT_TYPE_ALIASES[normalized]
    
    # Try partial match
    for valid_type in VALID_PRODUCT_TYPES:
        if valid_type in normalized or normalized in valid_type:
            return True, PRODUCT_TYPE_ALIASES.get(valid_type, valid_type)
    
    return False, normalized


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
        
        if qty < 10:
            return False, 0, "Minimum order quantity is 10 units"
        
        if qty > 10000:
            return False, 0, "Maximum order quantity is 10,000 units per order"
        
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
        
        if days < 3:
            return False, 0, "Minimum lead time is 3 days"
        
        if days > 90:
            return False, 0, "Maximum lead time is 90 days"
        
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
        r'(\d{1,3}(?:,\d{3})*)\s*(?:units?|pieces?|items?|pcs?|shirts?|hoodies?|caps?)',
        r'(?:need|want|order|require|looking for)\s*(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*(?:of|x)\s*',
        r'quantity[:\s]+(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*(?:total|altogether)',
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
        "t-shirt": ["t-shirt", "tshirt", "t shirt", "tee"],
        "polo": ["polo", "polo shirt"],
        "hoodie": ["hoodie", "hooded", "hoody", "sweatshirt"],
        "cap": ["cap", "hat", "baseball cap"],
        "mug": ["mug", "cup", "coffee mug"],
        "tote_bag": ["tote", "bag", "tote bag"],
        "jacket": ["jacket", "coat"],
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
        "product_type": "What type of product do you need? (t-shirt, polo, hoodie, cap, mug, tote bag, jacket)",
        "quantity": "How many units do you need? (minimum 10 units)",
        "delivery_address": "What is the delivery address for this order?",
        "material": "What material would you prefer? (cotton, polyester, blend)",
        "logo_description": "Please describe your logo or design (or attach an image reference)",
        "logo_color": "What color(s) should the logo be?",
        "logo_placement": "Where should the logo be placed? (front, back, sleeve, pocket)",
        "size_distribution": "How many of each size do you need? (e.g., 10 Small, 50 Medium, 40 Large)",
        "timeline": "When do you need the order delivered?",
        "budget": "What is your budget for this order?",
    }
    
    result = []
    for field in missing_fields:
        # Handle fields with additional info like "quantity (must be positive)"
        base_field = field.split(" (")[0]
        if base_field in descriptions:
            result.append(descriptions[base_field])
        else:
            # Convert snake_case to readable
            readable = field.replace("_", " ").title()
            result.append(f"Please provide: {readable}")
    
    return result


def validate_complete_order(requirements: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    """Comprehensive validation for order completeness.
    
    Args:
        requirements: Dictionary of extracted requirements
    
    Returns:
        Tuple of (is_complete, missing_required, missing_recommended)
    """
    missing_required = []
    missing_recommended = []
    
    req_data = requirements.get("requirements", requirements)
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        value = req_data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_required.append(field)
    
    # Check conditional fields if customization requested
    if check_customization_requested(req_data):
        for field in CUSTOMIZATION_REQUIRED_FIELDS:
            value = req_data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_required.append(field)
    
    # Check helpful fields
    for field in HELPFUL_FIELDS:
        value = req_data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing_recommended.append(field)
    
    is_complete = len(missing_required) == 0
    
    return is_complete, missing_required, missing_recommended
