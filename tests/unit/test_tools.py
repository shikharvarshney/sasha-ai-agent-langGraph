"""Unit tests for LangChain tools"""

import json
import pytest
from sasha_sales_ai.tools.feasibility_tool import (
    check_product_feasibility,
    get_product_specifications,
    list_available_products,
)
from sasha_sales_ai.tools.pricing_tool import (
    calculate_price,
    get_pricing_tiers,
    estimate_quick_price,
)


class TestFeasibilityTool:
    """Tests for feasibility checking tool"""
    
    def test_feasible_order(self):
        """Test a feasible order"""
        result = check_product_feasibility.invoke({
            "product_type": "widget",
            "quantity": 100,
        })
        data = json.loads(result)
        
        assert data["is_feasible"] is True
    
    def test_invalid_product_type(self):
        """Test with invalid product type"""
        result = check_product_feasibility.invoke({
            "product_type": "invalid_product",
            "quantity": 100,
        })
        data = json.loads(result)
        
        assert data["is_feasible"] is False
        assert "catalog" in data["reason"].lower()
    
    def test_quantity_below_minimum(self):
        """Test quantity below minimum"""
        result = check_product_feasibility.invoke({
            "product_type": "widget",
            "quantity": 5,  # min is 10
        })
        data = json.loads(result)
        
        assert data["is_feasible"] is False
        assert "minimum" in data["reason"].lower()
    
    def test_quantity_above_maximum(self):
        """Test quantity above maximum"""
        result = check_product_feasibility.invoke({
            "product_type": "widget",
            "quantity": 50000,  # max is 10000
        })
        data = json.loads(result)
        
        assert data["is_feasible"] is False
        assert "maximum" in data["reason"].lower()
    
    def test_timeline_too_short(self):
        """Test timeline shorter than minimum"""
        result = check_product_feasibility.invoke({
            "product_type": "widget",
            "quantity": 100,
            "timeline_days": 1,  # min is 3
        })
        data = json.loads(result)
        
        assert data["is_feasible"] is False
        assert "production time" in data["reason"].lower()
    
    def test_customization_not_available(self):
        """Test customization for product that doesn't support it"""
        result = check_product_feasibility.invoke({
            "product_type": "component",  # no customization
            "quantity": 1000,
            "customizations": "logo printing",
        })
        data = json.loads(result)
        
        assert data["is_feasible"] is False
        assert "customization" in data["reason"].lower()


class TestGetProductSpecifications:
    """Tests for product specifications tool"""
    
    def test_valid_product(self):
        """Test getting specs for valid product"""
        result = get_product_specifications.invoke({
            "product_type": "widget",
        })
        data = json.loads(result)
        
        assert "product_type" in data
        assert data["product_type"] == "widget"
        assert "min_quantity" in data
        assert "max_quantity" in data
    
    def test_invalid_product(self):
        """Test getting specs for invalid product"""
        result = get_product_specifications.invoke({
            "product_type": "invalid",
        })
        data = json.loads(result)
        
        assert "error" in data
        assert "available_products" in data


class TestListAvailableProducts:
    """Tests for list products tool"""
    
    def test_list_products(self):
        """Test listing all products"""
        result = list_available_products.invoke({})
        data = json.loads(result)
        
        assert "products" in data
        assert len(data["products"]) == 4
        
        product_names = [p["name"] for p in data["products"]]
        assert "widget" in product_names
        assert "gadget" in product_names


class TestPricingTool:
    """Tests for pricing calculation tool"""
    
    def test_basic_price(self):
        """Test basic price calculation"""
        result = calculate_price.invoke({
            "product_type": "widget",
            "quantity": 100,
        })
        data = json.loads(result)
        
        assert "grand_total" in data
        assert data["grand_total"] == 475.0  # 100 * 5 * 0.95 (5% discount)
    
    def test_volume_discount(self):
        """Test volume discount is applied"""
        result = calculate_price.invoke({
            "product_type": "widget",
            "quantity": 1000,
        })
        data = json.loads(result)
        
        # 1000+ units = 15% discount
        expected = 1000 * 5.00 * 0.85
        assert data["grand_total"] == expected
    
    def test_customization_pricing(self):
        """Test customization adds to price"""
        result = calculate_price.invoke({
            "product_type": "widget",
            "quantity": 100,
            "customizations": "logo_printing",
        })
        data = json.loads(result)
        
        # Base: 100 * 5 = 500, -5% discount = 475
        # Plus logo printing: 100 * 0.50 = 50
        # Total: 525
        assert data["grand_total"] == 525.0
    
    def test_rush_surcharge(self):
        """Test rush delivery surcharge"""
        result = calculate_price.invoke({
            "product_type": "widget",
            "quantity": 100,
            "timeline_days": 3,
        })
        data = json.loads(result)
        
        # Base: 100 * 5 = 500, -5% = 475
        # Rush (3 days = 50% surcharge on base): 500 * 0.5 = 250
        # Total: 475 + 250 = 725
        assert data["grand_total"] == 725.0
    
    def test_invalid_product(self):
        """Test with invalid product type"""
        result = calculate_price.invoke({
            "product_type": "invalid",
            "quantity": 100,
        })
        data = json.loads(result)
        
        assert "error" in data


class TestGetPricingTiers:
    """Tests for pricing tiers info"""
    
    def test_get_tiers(self):
        """Test getting pricing tier info"""
        result = get_pricing_tiers.invoke({})
        data = json.loads(result)
        
        assert "base_prices" in data
        assert "volume_discounts" in data
        assert "customizations" in data
        assert "rush_delivery" in data


class TestEstimateQuickPrice:
    """Tests for quick price estimate"""
    
    def test_quick_estimate(self):
        """Test quick price estimate"""
        result = estimate_quick_price.invoke({
            "product_type": "widget",
            "quantity": 100,
        })
        
        assert "475" in result  # 100 * 5 * 0.95
    
    def test_invalid_product(self):
        """Test with invalid product"""
        result = estimate_quick_price.invoke({
            "product_type": "invalid",
            "quantity": 100,
        })
        
        assert "unknown" in result.lower()

