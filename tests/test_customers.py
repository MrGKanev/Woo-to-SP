"""Tests for CustomerMigrationTool."""

import pytest
import pandas as pd

from woo_to_sp.config import CustomerConfig
from woo_to_sp.customers.customers import CustomerMigrationTool


class TestCustomerMigrationTool:
    """Test CustomerMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        return CustomerMigrationTool(CustomerConfig(show_progress=False))

    def test_validate_item_valid(self, tool):
        customer = pd.Series({"Email": "test@example.com"})
        is_valid, errors = tool.validate_item(customer)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_email(self, tool):
        customer = pd.Series({"Email": ""})
        is_valid, errors = tool.validate_item(customer)
        assert is_valid is False
        assert any("email" in e.lower() for e in errors)

    def test_validate_item_duplicate_email(self, tool):
        tool.seen_emails.add("dupe@example.com")
        customer = pd.Series({"Email": "dupe@example.com"})
        is_valid, errors = tool.validate_item(customer)
        assert is_valid is False
        assert tool.stats["duplicates_skipped"] == 1

    def test_parse_address_json_string(self, tool):
        addr_json = '{"address_1": "123 Main St", "city": "NYC", "state": "NY"}'
        result = tool.parse_address(addr_json)
        assert result["address_1"] == "123 Main St"
        assert result["city"] == "NYC"

    def test_parse_address_dict(self, tool):
        addr = {"address_1": "456 Oak Ave", "city": "LA"}
        result = tool.parse_address(addr)
        assert result["address_1"] == "456 Oak Ave"

    def test_parse_address_none(self, tool):
        assert tool.parse_address(None) == {}

    def test_parse_address_invalid_json(self, tool):
        assert tool.parse_address("{invalid json") == {}

    def test_parse_address_empty_string(self, tool):
        assert tool.parse_address("") == {}

    def test_convert_item_basic(self, tool):
        customer = pd.Series({
            "Email": "test@example.com",
            "First Name": "John",
            "Last Name": "Doe",
            "Billing Address": '{"address_1": "123 Main St", "city": "NYC", "state": "NY", "postcode": "10001", "country": "US"}',
            "Shipping Address": "{}",
            "Accepts Marketing": "yes",
            "Total Spent": 100.00,
            "Order Count": 2,
        })

        result = tool.convert_item(customer)

        assert result is not None
        assert result["Email"] == "test@example.com"
        assert result["First Name"] == "John"
        assert result["Last Name"] == "Doe"
        assert result["Address1"] == "123 Main St"
        assert result["City"] == "NYC"
        assert result["Accepts Marketing"] is True
        assert result["Tags"] == "Woocommerce Import"
        assert "test@example.com" in tool.seen_emails

    def test_convert_item_no_marketing(self, tool):
        customer = pd.Series({
            "Email": "no-marketing@example.com",
            "Accepts Marketing": "no",
        })
        result = tool.convert_item(customer)
        assert result["Accepts Marketing"] is False

    def test_convert_item_email_normalized(self, tool):
        customer = pd.Series({
            "Email": " TEST@Example.COM ",
            "Accepts Marketing": "no",
        })
        result = tool.convert_item(customer)
        assert result["Email"] == "test@example.com"

    def test_convert_mailchimp_subscriber(self, tool):
        subscriber = {
            "Email Address": "mc@example.com",
            "First Name": "Jane",
            "Last Name": "Smith",
            "Status": "subscribed",
        }
        result = tool.convert_mailchimp_subscriber(subscriber)
        assert result is not None
        assert result["Email"] == "mc@example.com"
        assert result["First Name"] == "Jane"
        assert result["Accepts Marketing"] is True
        assert "MailChimp Import" in result["Tags"]
        assert tool.stats["mailchimp_subscribers"] == 1

    def test_convert_mailchimp_subscriber_duplicate(self, tool):
        tool.seen_emails.add("dupe@example.com")
        subscriber = {"Email Address": "dupe@example.com"}
        result = tool.convert_mailchimp_subscriber(subscriber)
        assert result is None
        assert tool.stats["duplicates_skipped"] == 1

    def test_deduplication_across_sources(self, tool):
        """WooCommerce customer processed first, MailChimp skipped."""
        woo_customer = pd.Series({
            "Email": "both@example.com",
            "Accepts Marketing": "yes",
        })
        tool.validate_item(woo_customer)
        tool.convert_item(woo_customer)

        mc_subscriber = {"Email Address": "both@example.com"}
        result = tool.convert_mailchimp_subscriber(mc_subscriber)
        assert result is None
