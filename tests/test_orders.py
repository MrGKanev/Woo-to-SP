"""Tests for OrderMigrationTool."""

import pytest
import pandas as pd

from woo_to_sp.config import OrderConfig
from woo_to_sp.orders.orders import OrderMigrationTool


class TestOrderMigrationTool:
    """Test OrderMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        return OrderMigrationTool(OrderConfig(show_progress=False))

    def test_validate_item_valid(self, tool):
        order = pd.Series({
            "order_number": "1001",
            "customer_email": "test@example.com",
        })
        is_valid, errors = tool.validate_item(order)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_order_number(self, tool):
        order = pd.Series({
            "order_number": "",
            "customer_email": "test@example.com",
        })
        is_valid, errors = tool.validate_item(order)
        assert is_valid is False
        assert any("order number" in e.lower() for e in errors)

    def test_validate_item_missing_email(self, tool):
        order = pd.Series({
            "order_number": "1001",
            "customer_email": "",
        })
        is_valid, errors = tool.validate_item(order)
        assert is_valid is False
        assert any("email" in e.lower() for e in errors)

    def test_validate_item_both_missing(self, tool):
        order = pd.Series({
            "order_number": "",
            "customer_email": "",
        })
        is_valid, errors = tool.validate_item(order)
        assert is_valid is False
        assert len(errors) == 2

    def test_convert_item_basic(self, tool):
        order = pd.Series({
            "order_number": "1001",
            "customer_email": "customer@example.com",
            "status": "completed",
            "order_currency": "USD",
            "order_date": "2024-01-15 10:30:00",
            "billing_first_name": "John",
            "billing_last_name": "Doe",
            "billing_address_1": "123 Main St",
            "billing_city": "New York",
            "billing_state": "NY",
            "billing_postcode": "10001",
            "billing_country": "US",
            "billing_phone": "555-1234",
            "order_total": 99.99,
            "line_item_1": "name:Test Product|quantity:1|total:99.99|sku:TP001",
        })

        result = tool.convert_item(order)

        assert result is not None
        assert len(result) == 1
        assert result[0]["Name"] == "#1001"
        assert result[0]["Email"] == "customer@example.com"
        assert result[0]["Financial Status"] == "paid"
        assert result[0]["Fulfillment Status"] == "fulfilled"
        assert result[0]["Lineitem name"] == "Test Product"
        assert result[0]["Lineitem quantity"] == 1
        assert result[0]["Lineitem price"] == 99.99
        assert result[0]["Lineitem sku"] == "TP001"
        assert result[0]["Total"] == 99.99

    def test_convert_item_multiple_line_items(self, tool):
        order = pd.Series({
            "order_number": "1002",
            "customer_email": "customer@example.com",
            "status": "completed",
            "order_total": 50.00,
            "line_item_1": "name:Product A|quantity:2|total:30.00|sku:A001",
            "line_item_2": "name:Product B|quantity:1|total:20.00|sku:B001",
        })

        result = tool.convert_item(order)

        assert result is not None
        assert len(result) == 2
        assert result[0]["Lineitem name"] == "Product A"
        assert result[1]["Lineitem name"] == "Product B"
        # Totals only on first row
        assert "Total" in result[0]
        assert "Total" not in result[1]

    def test_convert_item_pending_order(self, tool):
        order = pd.Series({
            "order_number": "1003",
            "customer_email": "customer@example.com",
            "status": "pending",
            "line_item_1": "name:Pending Item|quantity:1|total:25.00",
        })

        result = tool.convert_item(order)

        assert result[0]["Financial Status"] == "pending"
        assert result[0]["Fulfillment Status"] == "unfulfilled"

    def test_convert_item_no_line_items(self, tool):
        order = pd.Series({
            "order_number": "1004",
            "customer_email": "customer@example.com",
            "status": "completed",
        })

        result = tool.convert_item(order)
        assert result is None

    def test_format_meta_name_with_mapping(self, tool):
        tool.meta_mapping = {
            "color": {
                "name_prefix": "Custom",
                "name_suffix": "Option",
                "sku_prefix": "CLR-",
                "price_field": "",
            }
        }
        result = tool.format_meta_name("color", "Red")
        assert result == "Custom Red Option"

    def test_format_meta_name_suffix_only(self, tool):
        tool.meta_mapping = {
            "size": {
                "name_prefix": "",
                "name_suffix": "Size",
                "sku_prefix": "",
                "price_field": "",
            }
        }
        result = tool.format_meta_name("size", "Large")
        assert result == "Large Size"

    def test_format_meta_name_no_mapping(self, tool):
        result = tool.format_meta_name("unknown", "value")
        assert result == "value"

    def test_parse_meta_info_empty(self, tool):
        assert tool.parse_meta_info("") == []
        assert tool.parse_meta_info(None) == []

    def test_line_item_price_calculation(self, tool):
        """Price = total / quantity."""
        order = pd.Series({
            "order_number": "1005",
            "customer_email": "test@example.com",
            "status": "completed",
            "line_item_1": "name:Bulk Item|quantity:3|total:30.00|sku:BLK",
        })
        result = tool.convert_item(order)
        assert result[0]["Lineitem price"] == 10.0
