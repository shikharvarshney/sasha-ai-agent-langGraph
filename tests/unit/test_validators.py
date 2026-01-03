"""Unit tests for validators"""

import pytest
from sasha_sales_ai.validators import (
    validate_requirements,
    validate_email_address,
    validate_product_type,
    validate_quantity,
    validate_timeline,
    extract_quantity_from_text,
    extract_product_type_from_text,
    get_missing_fields_description,
)


class TestValidateRequirements:
    """Tests for validate_requirements function"""
    
    def test_valid_requirements(self):
        """Test with all required fields present"""
        requirements = {
            "product_type": "widget",
            "quantity": 100,
        }
        is_valid, missing = validate_requirements(requirements)
        
        assert is_valid is True
        assert missing == []
    
    def test_missing_product_type(self):
        """Test with missing product type"""
        requirements = {
            "quantity": 100,
        }
        is_valid, missing = validate_requirements(requirements)
        
        assert is_valid is False
        assert "product_type" in missing
    
    def test_missing_quantity(self):
        """Test with missing quantity"""
        requirements = {
            "product_type": "widget",
        }
        is_valid, missing = validate_requirements(requirements)
        
        assert is_valid is False
        assert "quantity" in missing
    
    def test_empty_requirements(self):
        """Test with empty requirements"""
        requirements = {}
        is_valid, missing = validate_requirements(requirements)
        
        assert is_valid is False
        assert len(missing) == 2
    
    def test_invalid_quantity(self):
        """Test with invalid quantity (negative)"""
        requirements = {
            "product_type": "widget",
            "quantity": -5,
        }
        is_valid, missing = validate_requirements(requirements)
        
        assert is_valid is False


class TestValidateEmailAddress:
    """Tests for email validation"""
    
    def test_valid_email(self):
        """Test with valid email"""
        assert validate_email_address("test@example.com") is True
    
    def test_invalid_email_no_at(self):
        """Test with missing @ symbol"""
        assert validate_email_address("testexample.com") is False
    
    def test_invalid_email_no_domain(self):
        """Test with missing domain"""
        assert validate_email_address("test@") is False
    
    def test_invalid_email_empty(self):
        """Test with empty string"""
        assert validate_email_address("") is False


class TestValidateProductType:
    """Tests for product type validation"""
    
    def test_valid_product_types(self):
        """Test valid product types"""
        for product in ["widget", "gadget", "component", "assembly"]:
            is_valid, normalized = validate_product_type(product)
            assert is_valid is True
            assert normalized == product
    
    def test_case_insensitive(self):
        """Test case insensitivity"""
        is_valid, normalized = validate_product_type("WIDGET")
        assert is_valid is True
        assert normalized == "widget"
    
    def test_alias_handling(self):
        """Test alias handling"""
        is_valid, normalized = validate_product_type("widgets")
        assert is_valid is True
        assert normalized == "widget"
    
    def test_invalid_product_type(self):
        """Test invalid product type"""
        is_valid, normalized = validate_product_type("invalid")
        assert is_valid is False


class TestValidateQuantity:
    """Tests for quantity validation"""
    
    def test_valid_quantity(self):
        """Test valid quantity"""
        is_valid, qty, error = validate_quantity(100)
        assert is_valid is True
        assert qty == 100
        assert error == ""
    
    def test_string_quantity(self):
        """Test quantity as string"""
        is_valid, qty, error = validate_quantity("1,000")
        assert is_valid is True
        assert qty == 1000
    
    def test_negative_quantity(self):
        """Test negative quantity"""
        is_valid, qty, error = validate_quantity(-5)
        assert is_valid is False
        assert "positive" in error.lower()
    
    def test_zero_quantity(self):
        """Test zero quantity"""
        is_valid, qty, error = validate_quantity(0)
        assert is_valid is False
    
    def test_exceeds_max(self):
        """Test quantity exceeding maximum"""
        is_valid, qty, error = validate_quantity(200000)
        assert is_valid is False
        assert "exceeds" in error.lower()


class TestValidateTimeline:
    """Tests for timeline validation"""
    
    def test_valid_days(self):
        """Test valid timeline in days"""
        is_valid, days, error = validate_timeline(14)
        assert is_valid is True
        assert days == 14
    
    def test_weeks_string(self):
        """Test timeline as weeks string"""
        is_valid, days, error = validate_timeline("2 weeks")
        assert is_valid is True
        assert days == 14
    
    def test_months_string(self):
        """Test timeline as months string"""
        is_valid, days, error = validate_timeline("1 month")
        assert is_valid is True
        assert days == 30
    
    def test_exceeds_max_timeline(self):
        """Test timeline exceeding maximum"""
        is_valid, days, error = validate_timeline(500)
        assert is_valid is False


class TestExtractQuantityFromText:
    """Tests for quantity extraction"""
    
    def test_extract_with_units(self):
        """Test extraction with units keyword"""
        qty = extract_quantity_from_text("I need 100 units")
        assert qty == 100
    
    def test_extract_with_pieces(self):
        """Test extraction with pieces keyword"""
        qty = extract_quantity_from_text("Order 500 pieces please")
        assert qty == 500
    
    def test_extract_with_commas(self):
        """Test extraction with comma-separated number"""
        qty = extract_quantity_from_text("We need 1,000 items")
        assert qty == 1000
    
    def test_no_quantity(self):
        """Test when no quantity present"""
        qty = extract_quantity_from_text("I need some widgets")
        assert qty is None


class TestExtractProductTypeFromText:
    """Tests for product type extraction"""
    
    def test_extract_widget(self):
        """Test widget extraction"""
        product = extract_product_type_from_text("I need widgets")
        assert product == "widget"
    
    def test_extract_gadget(self):
        """Test gadget extraction"""
        product = extract_product_type_from_text("Order some gadgets")
        assert product == "gadget"
    
    def test_no_product(self):
        """Test when no product mentioned"""
        product = extract_product_type_from_text("I need some stuff")
        assert product is None


class TestGetMissingFieldsDescription:
    """Tests for missing fields description"""
    
    def test_product_type_description(self):
        """Test product type description"""
        descriptions = get_missing_fields_description(["product_type"])
        assert len(descriptions) == 1
        assert "type of product" in descriptions[0].lower()
    
    def test_quantity_description(self):
        """Test quantity description"""
        descriptions = get_missing_fields_description(["quantity"])
        assert len(descriptions) == 1
        assert "how many" in descriptions[0].lower()
    
    def test_multiple_fields(self):
        """Test multiple missing fields"""
        descriptions = get_missing_fields_description(["product_type", "quantity"])
        assert len(descriptions) == 2

