"""
Woo-to-SP: WooCommerce to Shopify Migration Toolkit

A comprehensive toolkit for migrating data from WooCommerce to Shopify.
Supports products, customers, orders, categories, reviews, and discount codes.
"""

from .base.base_migration import BaseMigrationTool
from .products.products import ProductMigrationTool
from .customers.customers import CustomerMigrationTool
from .orders.orders import OrderMigrationTool
from .categories.categories import CollectionMigrationTool
from .reviews.review import ReviewMigrationTool
from .promocodes.promocode import DiscountMigrationTool

__version__ = "1.2.0"
__author__ = "Gabriel Kanev"

__all__ = [
    "BaseMigrationTool",
    "ProductMigrationTool",
    "CustomerMigrationTool",
    "OrderMigrationTool",
    "CollectionMigrationTool",
    "ReviewMigrationTool",
    "DiscountMigrationTool",
]
