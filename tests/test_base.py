"""Tests for BaseMigrationTool."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from base.base_migration import BaseMigrationTool


class TestBaseMigrationToolUtilities:
    """Test utility methods in BaseMigrationTool."""

    def test_clean_text_with_string(self):
        """Test clean_text with normal string."""
        assert BaseMigrationTool.clean_text("  hello world  ") == "hello world"

    def test_clean_text_with_none(self):
        """Test clean_text with None value."""
        assert BaseMigrationTool.clean_text(None) == ""

    def test_clean_text_with_number(self):
        """Test clean_text with numeric value."""
        assert BaseMigrationTool.clean_text(123) == "123"

    def test_create_handle_simple(self):
        """Test create_handle with simple string."""
        assert BaseMigrationTool.create_handle("Test Product") == "test-product"

    def test_create_handle_with_special_chars(self):
        """Test create_handle with special characters."""
        assert BaseMigrationTool.create_handle("Test! Product @#$%") == "test-product"

    def test_create_handle_with_multiple_spaces(self):
        """Test create_handle with multiple spaces."""
        assert BaseMigrationTool.create_handle("Test   Product") == "test-product"

    def test_create_handle_empty(self):
        """Test create_handle with empty string."""
        assert BaseMigrationTool.create_handle("") == ""

    def test_clean_phone_10_digit(self):
        """Test clean_phone with 10-digit US number."""
        assert BaseMigrationTool.clean_phone("555-123-4567") == "+15551234567"

    def test_clean_phone_with_country_code(self):
        """Test clean_phone with existing country code."""
        assert BaseMigrationTool.clean_phone("+1-555-123-4567") == "+15551234567"

    def test_clean_phone_empty(self):
        """Test clean_phone with empty value."""
        assert BaseMigrationTool.clean_phone("") == ""
        assert BaseMigrationTool.clean_phone(None) == ""

    def test_clean_html_basic(self):
        """Test clean_html removes tags."""
        html = "<p>Hello <strong>World</strong></p>"
        result = BaseMigrationTool.clean_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_clean_html_removes_scripts(self):
        """Test clean_html removes script tags."""
        html = "<p>Hello</p><script>alert('xss')</script><p>World</p>"
        result = BaseMigrationTool.clean_html(html)
        assert "alert" not in result
        assert "script" not in result

    def test_clean_html_removes_shortcodes(self):
        """Test clean_html removes WordPress shortcodes."""
        html = "<p>Hello [gallery ids='1,2,3'] World</p>"
        result = BaseMigrationTool.clean_html(html)
        assert "[gallery" not in result
        assert "Hello" in result
        assert "World" in result

    def test_clean_html_empty(self):
        """Test clean_html with empty input."""
        assert BaseMigrationTool.clean_html("") == ""
        assert BaseMigrationTool.clean_html(None) == ""

    def test_format_date_standard_format(self):
        """Test format_date with standard format."""
        result = BaseMigrationTool.format_date("2024-01-15 10:30:00")
        assert result == "2024-01-15 10:30:00"

    def test_format_date_date_only(self):
        """Test format_date with date only."""
        result = BaseMigrationTool.format_date("2024-01-15")
        assert "2024-01-15" in result

    def test_format_date_us_format(self):
        """Test format_date with US date format."""
        result = BaseMigrationTool.format_date("01/15/2024")
        assert "2024-01-15" in result

    def test_format_date_empty(self):
        """Test format_date with empty input."""
        assert BaseMigrationTool.format_date("") == ""
        assert BaseMigrationTool.format_date(None) == ""

    def test_format_date_invalid(self):
        """Test format_date with invalid input."""
        assert BaseMigrationTool.format_date("not-a-date") == ""
