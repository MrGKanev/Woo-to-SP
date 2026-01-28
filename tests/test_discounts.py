"""Tests for DiscountMigrationTool."""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from promocodes.promocode import DiscountMigrationTool


class TestDiscountMigrationTool:
    """Test DiscountMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create a DiscountMigrationTool instance."""
        return DiscountMigrationTool({'show_progress': False})

    def test_validate_item_valid(self, tool):
        """Test validation with valid coupon data."""
        coupon = pd.Series({
            'code': 'SUMMER20',
            'amount': 20,
            'discount_type': 'percent',
        })
        is_valid, errors = tool.validate_item(coupon)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_code(self, tool):
        """Test validation with missing code."""
        coupon = pd.Series({
            'code': '',
            'amount': 20,
        })
        is_valid, errors = tool.validate_item(coupon)
        assert is_valid is False
        assert any('code' in e.lower() for e in errors)

    def test_validate_item_negative_amount(self, tool):
        """Test validation with negative amount."""
        coupon = pd.Series({
            'code': 'TEST',
            'amount': -10,
        })
        is_valid, errors = tool.validate_item(coupon)
        assert is_valid is False
        assert any('negative' in e.lower() for e in errors)

    def test_clean_discount_code_basic(self, tool):
        """Test cleaning discount code."""
        assert tool.clean_discount_code("summer20") == "SUMMER20"

    def test_clean_discount_code_special_chars(self, tool):
        """Test cleaning discount code with special characters."""
        assert tool.clean_discount_code("summer@20!") == "SUMMER20"

    def test_clean_discount_code_truncation(self, tool):
        """Test discount code truncation."""
        long_code = "A" * 60
        result = tool.clean_discount_code(long_code)
        assert len(result) == 50
        assert tool.stats['codes_truncated'] == 1

    def test_convert_amount_type_percent(self, tool):
        """Test converting percentage discount."""
        discount_type, amount = tool.convert_amount_type('percent', 20)
        assert discount_type == 'percentage'
        assert amount == 20
        assert tool.stats['percentage_discounts'] == 1

    def test_convert_amount_type_fixed_cart(self, tool):
        """Test converting fixed cart discount."""
        discount_type, amount = tool.convert_amount_type('fixed_cart', 10)
        assert discount_type == 'fixed_amount'
        assert amount == 10
        assert tool.stats['fixed_discounts'] == 1

    def test_convert_item_percentage(self, tool):
        """Test converting percentage coupon."""
        coupon = pd.Series({
            'code': 'SUMMER20',
            'discount_type': 'percent',
            'amount': 20,
            'minimum_amount': 50,
            'individual_use': 'yes',
            'enabled': 'yes',
            'date_created': '2024-01-01',
            'date_expires': '2024-12-31',
        })

        result = tool.convert_item(coupon)

        assert result is not None
        assert result['Discount Code'] == 'SUMMER20'
        assert result['Type'] == 'percentage'
        assert result['Amount'] == 20
        assert result['Minimum Purchase Amount'] == 50
        assert result['Once Per Customer'] is True
        assert result['Status'] == 'enabled'

    def test_convert_item_fixed(self, tool):
        """Test converting fixed amount coupon."""
        coupon = pd.Series({
            'code': 'FLAT10',
            'discount_type': 'fixed_cart',
            'amount': 10,
            'individual_use': 'no',
            'enabled': 'yes',
        })

        result = tool.convert_item(coupon)

        assert result['Type'] == 'fixed_amount'
        assert result['Amount'] == 10
        assert result['Once Per Customer'] is False

    def test_process_product_restrictions(self, tool):
        """Test product restrictions processing."""
        restrictions = tool.process_product_restrictions(
            included_products='1,2,3',
            excluded_products='4,5'
        )

        assert restrictions['entitled_product_ids'] == ['1', '2', '3']
        assert restrictions['excluded_product_ids'] == ['4', '5']

    def test_process_product_restrictions_empty(self, tool):
        """Test product restrictions with empty values."""
        restrictions = tool.process_product_restrictions('', '')

        assert restrictions['entitled_product_ids'] == []
        assert restrictions['excluded_product_ids'] == []
