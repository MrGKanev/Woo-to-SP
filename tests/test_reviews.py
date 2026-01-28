"""Tests for ReviewMigrationTool."""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reviews.review import ReviewMigrationTool


class TestReviewMigrationTool:
    """Test ReviewMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create a ReviewMigrationTool instance."""
        return ReviewMigrationTool({'show_progress': False})

    def test_validate_item_valid(self, tool):
        """Test validation with valid review data."""
        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_content': 'Great product!',
            'rating': 5,
        })
        is_valid, errors = tool.validate_item(review)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_required(self, tool):
        """Test validation with missing required fields."""
        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': None,
            'comment_author': '',
            'comment_content': 'Great product!',
        })
        is_valid, errors = tool.validate_item(review)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_item_invalid_rating(self, tool):
        """Test validation with invalid rating."""
        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_content': 'Great product!',
            'rating': 10,  # Invalid: > 5
        })
        is_valid, errors = tool.validate_item(review)
        assert is_valid is False
        assert any('Rating' in e for e in errors)

    def test_convert_item_basic(self, tool):
        """Test converting a basic review."""
        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_author_email': 'john@example.com',
            'comment_content': 'Great product!',
            'comment_date': '2024-01-15 10:30:00',
            'rating': 5,
            'comment_approved': '1',
            'verified': '1',
        })

        result = tool.convert_item(review)

        assert result is not None
        assert result['Reviewer Name'] == 'John Doe'
        assert result['Reviewer Email'] == 'john@example.com'
        assert result['Rating'] == 5
        assert result['Review Status'] == 'published'
        assert result['Verified Buyer'] is True

    def test_convert_item_with_html(self, tool):
        """Test converting review with HTML content."""
        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_content': '<p>This is a <strong>great</strong> product!</p>',
            'rating': 5,
            'comment_approved': '1',
        })

        result = tool.convert_item(review)

        assert '<' not in result['Review Text']
        assert 'great' in result['Review Text']

    def test_convert_item_unpublished(self, tool):
        """Test converting unpublished review."""
        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_content': 'Pending review',
            'rating': 3,
            'comment_approved': '0',
        })

        result = tool.convert_item(review)

        assert result['Review Status'] == 'unpublished'

    def test_product_mapping(self, tool):
        """Test product mapping is applied."""
        tool.product_mapping = {'101': 'mapped-product-handle'}

        review = pd.Series({
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_content': 'Great!',
            'rating': 5,
        })

        result = tool.convert_item(review)

        assert result['Product Handle'] == 'mapped-product-handle'
