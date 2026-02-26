"""Tests for BaseMigrationTool and utility functions."""

import pandas as pd
import pytest

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.utils import (
    clean_html,
    clean_phone,
    clean_text,
    create_handle,
    format_date,
    parse_json_field,
)


class TestUtilityFunctions:
    """Test standalone utility functions."""

    def test_clean_text_with_string(self):
        assert clean_text("  hello world  ") == "hello world"

    def test_clean_text_with_none(self):
        assert clean_text(None) == ""

    def test_clean_text_with_number(self):
        assert clean_text(123) == "123"

    def test_clean_text_with_nan(self):
        assert clean_text(pd.NA) == ""

    def test_create_handle_simple(self):
        assert create_handle("Test Product") == "test-product"

    def test_create_handle_with_special_chars(self):
        assert create_handle("Test! Product @#$%") == "test-product"

    def test_create_handle_with_multiple_spaces(self):
        assert create_handle("Test   Product") == "test-product"

    def test_create_handle_empty(self):
        assert create_handle("") == ""

    def test_clean_phone_10_digit(self):
        assert clean_phone("555-123-4567") == "+15551234567"

    def test_clean_phone_with_country_code(self):
        assert clean_phone("+1-555-123-4567") == "+15551234567"

    def test_clean_phone_empty(self):
        assert clean_phone("") == ""
        assert clean_phone(None) == ""

    def test_clean_html_basic(self):
        html = "<p>Hello <strong>World</strong></p>"
        result = clean_html(html)
        assert "Hello" in result
        assert "World" in result
        assert "<" not in result

    def test_clean_html_removes_scripts(self):
        html = "<p>Hello</p><script>alert('xss')</script><p>World</p>"
        result = clean_html(html)
        assert "alert" not in result
        assert "script" not in result

    def test_clean_html_removes_shortcodes(self):
        html = "<p>Hello [gallery ids='1,2,3'] World</p>"
        result = clean_html(html)
        assert "[gallery" not in result
        assert "Hello" in result
        assert "World" in result

    def test_clean_html_empty(self):
        assert clean_html("") == ""
        assert clean_html(None) == ""

    def test_format_date_standard_format(self):
        result = format_date("2024-01-15 10:30:00")
        assert result == "2024-01-15 10:30:00"

    def test_format_date_date_only(self):
        result = format_date("2024-01-15")
        assert "2024-01-15" in result

    def test_format_date_us_format(self):
        result = format_date("01/15/2024")
        assert "2024-01-15" in result

    def test_format_date_empty(self):
        assert format_date("") == ""
        assert format_date(None) == ""

    def test_format_date_invalid(self):
        assert format_date("not-a-date") == ""

    def test_parse_json_field_string(self):
        result = parse_json_field('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_field_list_string(self):
        result = parse_json_field("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_parse_json_field_already_dict(self):
        result = parse_json_field({"key": "value"})
        assert result == {"key": "value"}

    def test_parse_json_field_none(self):
        result = parse_json_field(None)
        assert result == {}

    def test_parse_json_field_invalid(self):
        result = parse_json_field("not json")
        assert result == {}

    def test_parse_json_field_default(self):
        result = parse_json_field(None, default=[])
        assert result == []


class TestBaseMigrationToolDelegation:
    """Test that BaseMigrationTool static methods delegate to utils."""

    def test_clean_text_delegates(self):
        assert BaseMigrationTool.clean_text("  hello world  ") == "hello world"

    def test_create_handle_delegates(self):
        assert BaseMigrationTool.create_handle("Test Product") == "test-product"

    def test_clean_phone_delegates(self):
        assert BaseMigrationTool.clean_phone("555-123-4567") == "+15551234567"

    def test_clean_html_delegates(self):
        result = BaseMigrationTool.clean_html("<p>Hello</p>")
        assert "Hello" in result
        assert "<" not in result

    def test_format_date_delegates(self):
        result = BaseMigrationTool.format_date("2024-01-15 10:30:00")
        assert result == "2024-01-15 10:30:00"
