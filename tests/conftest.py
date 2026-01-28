"""Pytest configuration and shared fixtures."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_products_df():
    """Create sample WooCommerce products DataFrame."""
    return pd.DataFrame([
        {
            'ID': 1,
            'post_title': 'Test Product 1',
            'post_content': '<p>This is a test product</p>',
            'status': 'publish',
            'vendor': 'Test Vendor',
            'product_type': 'simple',
            'tags': 'test, sample',
            'variations': '[]',
            'images': '[]',
        },
        {
            'ID': 2,
            'post_title': 'Test Product 2',
            'post_content': '<p>Another test product</p>',
            'status': 'draft',
            'vendor': 'Test Vendor',
            'product_type': 'variable',
            'tags': 'test',
            'variations': '[{"sku": "TP2-VAR1", "price": 29.99}]',
            'images': '["https://example.com/image1.jpg"]',
        },
    ])


@pytest.fixture
def sample_customers_df():
    """Create sample WooCommerce customers DataFrame."""
    return pd.DataFrame([
        {
            'Email': 'test1@example.com',
            'First Name': 'John',
            'Last Name': 'Doe',
            'Billing Address': '{"address_1": "123 Main St", "city": "New York", "state": "NY", "postcode": "10001", "country": "US"}',
            'Shipping Address': '{}',
            'Accepts Marketing': 'yes',
            'Total Spent': 100.00,
            'Order Count': 2,
        },
        {
            'Email': 'test2@example.com',
            'First Name': 'Jane',
            'Last Name': 'Smith',
            'Billing Address': '{}',
            'Shipping Address': '{}',
            'Accepts Marketing': 'no',
            'Total Spent': 0,
            'Order Count': 0,
        },
    ])


@pytest.fixture
def sample_orders_df():
    """Create sample WooCommerce orders DataFrame."""
    return pd.DataFrame([
        {
            'order_number': '1001',
            'customer_email': 'customer@example.com',
            'status': 'completed',
            'order_currency': 'USD',
            'order_date': '2024-01-15 10:30:00',
            'billing_first_name': 'John',
            'billing_last_name': 'Doe',
            'billing_address_1': '123 Main St',
            'billing_city': 'New York',
            'billing_state': 'NY',
            'billing_postcode': '10001',
            'billing_country': 'US',
            'billing_phone': '555-1234',
            'order_total': 99.99,
            'line_item_1': 'name:Test Product|quantity:1|total:99.99|sku:TP001',
        },
    ])


@pytest.fixture
def sample_reviews_df():
    """Create sample WooCommerce reviews DataFrame."""
    return pd.DataFrame([
        {
            'comment_ID': 1,
            'comment_post_ID': 101,
            'comment_author': 'John Doe',
            'comment_author_email': 'john@example.com',
            'comment_content': 'Great product!',
            'comment_date': '2024-01-15 10:30:00',
            'rating': 5,
            'comment_approved': '1',
            'verified': '1',
        },
        {
            'comment_ID': 2,
            'comment_post_ID': 102,
            'comment_author': 'Jane Smith',
            'comment_author_email': 'jane@example.com',
            'comment_content': 'Good quality',
            'comment_date': '2024-01-16',
            'rating': 4,
            'comment_approved': '1',
            'verified': '0',
        },
    ])


@pytest.fixture
def sample_categories_df():
    """Create sample WooCommerce categories DataFrame."""
    return pd.DataFrame([
        {
            'term_id': 1,
            'name': 'Electronics',
            'slug': 'electronics',
            'description': 'Electronic products',
            'parent': None,
        },
        {
            'term_id': 2,
            'name': 'Clothing',
            'slug': 'clothing',
            'description': '<p>Fashion items</p>',
            'parent': None,
        },
    ])


@pytest.fixture
def sample_coupons_df():
    """Create sample WooCommerce coupons DataFrame."""
    return pd.DataFrame([
        {
            'code': 'SUMMER20',
            'discount_type': 'percent',
            'amount': 20,
            'minimum_amount': 50,
            'usage_limit': 100,
            'individual_use': 'yes',
            'enabled': 'yes',
            'date_created': '2024-01-01',
            'date_expires': '2024-12-31',
        },
        {
            'code': 'FLAT10',
            'discount_type': 'fixed_cart',
            'amount': 10,
            'minimum_amount': 0,
            'usage_limit': None,
            'individual_use': 'no',
            'enabled': 'yes',
        },
    ])
