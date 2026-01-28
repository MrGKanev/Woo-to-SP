"""Tests for CollectionMigrationTool."""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from categories.categories import CollectionMigrationTool


class TestCollectionMigrationTool:
    """Test CollectionMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create a CollectionMigrationTool instance."""
        return CollectionMigrationTool({'show_progress': False})

    def test_validate_item_valid(self, tool):
        """Test validation with valid category."""
        category = pd.Series({
            'term_id': 1,
            'name': 'Electronics',
            'slug': 'electronics',
        })
        is_valid, errors = tool.validate_item(category)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_name(self, tool):
        """Test validation with missing name."""
        category = pd.Series({
            'term_id': 1,
            'name': '',
            'slug': 'electronics',
        })
        is_valid, errors = tool.validate_item(category)
        assert is_valid is False

    def test_create_unique_handle_simple(self, tool):
        """Test creating unique handle."""
        handle = tool.create_unique_handle('Electronics')
        assert handle == 'electronics'
        assert 'electronics' in tool.processed_handles

    def test_create_unique_handle_duplicate(self, tool):
        """Test creating unique handle for duplicate."""
        handle1 = tool.create_unique_handle('Electronics')
        handle2 = tool.create_unique_handle('Electronics')

        assert handle1 == 'electronics'
        assert handle2 != 'electronics'
        assert handle2.startswith('electronics-')

    def test_extract_image_url_direct(self, tool):
        """Test extracting direct image URL."""
        url = tool.extract_image_url('https://example.com/image.jpg')
        assert url == 'https://example.com/image.jpg'

    def test_extract_image_url_json(self, tool):
        """Test extracting image URL from JSON."""
        json_data = '{"url": "https://example.com/image.jpg", "id": 1}'
        url = tool.extract_image_url(json_data)
        assert url == 'https://example.com/image.jpg'

    def test_extract_image_url_empty(self, tool):
        """Test extracting from empty value."""
        assert tool.extract_image_url('') == ''
        assert tool.extract_image_url(None) == ''

    def test_create_collection_rules(self, tool):
        """Test creating collection rules."""
        category = pd.Series({
            'name': 'Electronics',
            'slug': 'electronics',
        })

        rules = tool.create_collection_rules(category)

        assert len(rules) == 2
        assert rules[0]['column'] == 'tag'
        assert rules[0]['condition'] == 'category_electronics'
        assert rules[1]['column'] == 'type'
        assert rules[1]['condition'] == 'Electronics'

    def test_convert_item_basic(self, tool):
        """Test converting a basic category."""
        category = pd.Series({
            'term_id': 1,
            'name': 'Electronics',
            'slug': 'electronics',
            'description': '<p>Electronic products</p>',
        })

        result = tool.convert_item(category)

        assert result is not None
        assert result['Handle'] == 'electronics'
        assert result['Title'] == 'Electronics'
        assert result['Collection Type'] == 'smart'
        assert result['Published'] is True
        assert '<' not in result['Body HTML']

    def test_convert_item_manual_collection(self, tool):
        """Test converting with manual collection type."""
        tool.config['use_smart_collections'] = False

        category = pd.Series({
            'term_id': 1,
            'name': 'Electronics',
            'slug': 'electronics',
        })

        result = tool.convert_item(category)

        assert result['Collection Type'] == 'custom'
        assert result['Rules'] == ''

    def test_convert_item_with_parent(self, tool):
        """Test converting category with parent."""
        category = pd.Series({
            'term_id': 2,
            'name': 'Laptops',
            'slug': 'laptops',
            'parent': 1,
        })

        result = tool.convert_item(category)

        assert len(tool.parent_relations) == 1
        assert tool.parent_relations[0]['parent_id'] == 1
        assert tool.stats['parent_relations'] == 1

    def test_image_mapping(self, tool):
        """Test image mapping is applied."""
        tool.image_mapping = {'1': 'https://cdn.shopify.com/category1.jpg'}

        category = pd.Series({
            'term_id': 1,
            'name': 'Electronics',
            'slug': 'electronics',
        })

        result = tool.convert_item(category)

        assert result['Image Src'] == 'https://cdn.shopify.com/category1.jpg'
        assert tool.stats['images_processed'] == 1
