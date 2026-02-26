"""Tests for ReviewMigrationTool."""

import pytest
import pandas as pd

from woo_to_sp.config import ReviewConfig
from woo_to_sp.reviews.review import ReviewMigrationTool


class TestReviewMigrationTool:
    """Test ReviewMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        return ReviewMigrationTool(ReviewConfig(show_progress=False))

    def test_validate_item_valid(self, tool):
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "John Doe",
            "comment_content": "Great product!",
            "rating": 5,
        })
        is_valid, errors = tool.validate_item(review)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_required(self, tool):
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": None,
            "comment_author": "",
            "comment_content": "Great product!",
        })
        is_valid, errors = tool.validate_item(review)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_item_invalid_rating(self, tool):
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "John Doe",
            "comment_content": "Great product!",
            "rating": 10,
        })
        is_valid, errors = tool.validate_item(review)
        assert is_valid is False
        assert any("Rating" in e for e in errors)

    def test_convert_item_basic(self, tool):
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "John Doe",
            "comment_author_email": "john@example.com",
            "comment_content": "Great product!",
            "comment_date": "2024-01-15 10:30:00",
            "rating": 5,
            "comment_approved": "1",
            "verified": "1",
        })

        result = tool.convert_item(review)

        assert result is not None
        assert result["Reviewer Name"] == "John Doe"
        assert result["Reviewer Email"] == "john@example.com"
        assert result["Rating"] == 5
        assert result["Review Status"] == "published"
        assert result["Verified Buyer"] is True

    def test_convert_item_with_html(self, tool):
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "John Doe",
            "comment_content": "<p>This is a <strong>great</strong> product!</p>",
            "rating": 5,
            "comment_approved": "1",
        })

        result = tool.convert_item(review)

        assert "<" not in result["Review Text"]
        assert "great" in result["Review Text"]

    def test_convert_item_unpublished(self, tool):
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "John Doe",
            "comment_content": "Pending review",
            "rating": 3,
            "comment_approved": "0",
        })

        result = tool.convert_item(review)

        assert result["Review Status"] == "unpublished"

    def test_product_mapping(self, tool):
        tool.product_mapping = {"101": "mapped-product-handle"}

        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "John Doe",
            "comment_content": "Great!",
            "rating": 5,
        })

        result = tool.convert_item(review)

        assert result["Product Handle"] == "mapped-product-handle"

    def test_convert_item_clamps_rating(self, tool):
        """Rating above 5 gets clamped."""
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "Test",
            "comment_content": "Test",
            "rating": 99,
        })
        result = tool.convert_item(review)
        assert result["Rating"] == 5

    def test_convert_item_invalid_rating_uses_default(self, tool):
        """Non-numeric rating uses default."""
        review = pd.Series({
            "comment_ID": 1,
            "comment_post_ID": 101,
            "comment_author": "Test",
            "comment_content": "Test",
            "rating": "abc",
        })
        result = tool.convert_item(review)
        assert result["Rating"] == 5
