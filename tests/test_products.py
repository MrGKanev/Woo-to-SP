"""Tests for ProductMigrationTool."""

import pytest
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from products.products import ProductMigrationTool, ProductVariant


class TestProductVariant:
    """Test ProductVariant dataclass."""

    def test_default_values(self):
        """Test ProductVariant default values."""
        variant = ProductVariant()
        assert variant.sku == ""
        assert variant.price == 0.0
        assert variant.compare_at_price is None
        assert variant.weight == 0.0
        assert variant.weight_unit == "kg"
        assert variant.inventory_quantity == 0

    def test_custom_values(self):
        """Test ProductVariant with custom values."""
        variant = ProductVariant(
            sku="TEST-001",
            price=29.99,
            compare_at_price=39.99,
            weight=1.5,
            inventory_quantity=100
        )
        assert variant.sku == "TEST-001"
        assert variant.price == 29.99
        assert variant.compare_at_price == 39.99


class TestProductMigrationTool:
    """Test ProductMigrationTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create a ProductMigrationTool instance."""
        return ProductMigrationTool({'show_progress': False})

    def test_validate_item_valid(self, tool):
        """Test validation with valid product."""
        product = pd.Series({
            'ID': 1,
            'post_title': 'Test Product',
            'status': 'publish',
        })
        is_valid, errors = tool.validate_item(product)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_item_missing_title(self, tool):
        """Test validation with missing title."""
        product = pd.Series({
            'ID': 1,
            'post_title': '',
            'status': 'publish',
        })
        is_valid, errors = tool.validate_item(product)
        assert is_valid is False

    def test_validate_item_skip_drafts(self, tool):
        """Test validation skips drafts when configured."""
        tool.config['skip_drafts'] = True
        product = pd.Series({
            'ID': 1,
            'post_title': 'Draft Product',
            'status': 'draft',
        })
        is_valid, errors = tool.validate_item(product)
        assert is_valid is False
        assert tool.stats['drafts_skipped'] == 1

    def test_convert_item_basic(self, tool):
        """Test converting a basic product."""
        product = pd.Series({
            'ID': 1,
            'post_title': 'Test Product',
            'post_content': '<p>Product description</p>',
            'status': 'publish',
            'vendor': 'Test Vendor',
            'product_type': 'simple',
            'tags': 'test, sample',
            'variations': '[]',
            'images': '[]',
        })

        result = tool.convert_item(product)

        assert result is not None
        assert result['Handle'] == 'test-product'
        assert result['Title'] == 'Test Product'
        assert result['Vendor'] == 'Test Vendor'
        assert result['Type'] == 'simple'
        assert result['Published'] is True
        assert '<' not in result['Body (HTML)']

    def test_convert_item_draft(self, tool):
        """Test converting a draft product."""
        product = pd.Series({
            'ID': 1,
            'post_title': 'Draft Product',
            'post_content': '',
            'status': 'draft',
            'variations': '[]',
            'images': '[]',
        })

        result = tool.convert_item(product)

        assert result['Published'] is False

    def test_process_variants(self, tool):
        """Test processing variants."""
        variants_data = [
            {
                'sku': 'VAR-001',
                'price': 29.99,
                'regular_price': 39.99,
                'weight': 0.5,
                'stock_quantity': 10,
                'attribute_1': 'Red',
            },
            {
                'sku': 'VAR-002',
                'price': 29.99,
                'weight': 0.5,
                'stock_quantity': 5,
                'attribute_1': 'Blue',
            },
        ]

        variants = tool.process_variants(variants_data)

        assert len(variants) == 2
        assert variants[0].sku == 'VAR-001'
        assert variants[0].compare_at_price == 39.99
        assert variants[0].option1 == 'Red'
        assert variants[1].compare_at_price is None
        assert tool.stats['variants_processed'] == 2

    def test_process_images(self, tool):
        """Test processing images."""
        image_urls = [
            'https://example.com/image1.jpg',
            'https://example.com/image2.jpg',
        ]

        images = tool.process_images(image_urls, '1')

        assert len(images) == 2
        assert images[0]['src'] == 'https://example.com/image1.jpg'
        assert images[0]['position'] == 1
        assert images[1]['position'] == 2
        assert tool.stats['images_processed'] == 2

    def test_process_images_invalid_url(self, tool):
        """Test processing invalid image URLs."""
        image_urls = [
            'not-a-url',
            'https://example.com/valid.jpg',
        ]

        images = tool.process_images(image_urls, '1')

        assert len(images) == 1
        assert images[0]['src'] == 'https://example.com/valid.jpg'

    def test_process_images_disabled(self, tool):
        """Test image processing when disabled."""
        tool.config['image_migration'] = False
        image_urls = ['https://example.com/image.jpg']

        images = tool.process_images(image_urls, '1')

        assert len(images) == 0

    def test_image_mapping(self, tool):
        """Test image URL mapping."""
        tool.image_mapping = {
            'https://old.com/image.jpg': 'https://cdn.shopify.com/image.jpg'
        }

        images = tool.process_images(['https://old.com/image.jpg'], '1')

        assert images[0]['src'] == 'https://cdn.shopify.com/image.jpg'
