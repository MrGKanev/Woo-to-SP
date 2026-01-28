#!/usr/bin/env python3
"""
Woo-to-SP: WooCommerce to Shopify Migration CLI

A unified command-line interface for all migration tools.
"""

import argparse
import sys
import logging
from pathlib import Path

from products.products import ProductMigrationTool
from customers.customers import CustomerMigrationTool
from orders.orders import OrderMigrationTool
from categories.categories import CollectionMigrationTool
from reviews.review import ReviewMigrationTool
from promocodes.promocode import DiscountMigrationTool


def setup_logging(verbose: bool = False) -> None:
    """Configure global logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )


def cmd_products(args: argparse.Namespace) -> None:
    """Handle products migration command."""
    config = {
        'image_migration': not args.no_images,
        'inventory_tracking': True,
        'default_weight_unit': 'kg',
        'batch_size': 100,
        'skip_drafts': args.skip_drafts
    }
    tool = ProductMigrationTool(config)
    tool.convert_products(
        input_file=args.input,
        output_file=args.output,
        image_mapping_file=args.image_mapping
    )


def cmd_customers(args: argparse.Namespace) -> None:
    """Handle customers migration command."""
    if not args.woo_file and not args.mailchimp_folder:
        print("Error: At least one of --woo-file or --mailchimp-folder is required")
        sys.exit(1)

    tool = CustomerMigrationTool()
    tool.convert_customers(
        woo_file=args.woo_file,
        mailchimp_folder=args.mailchimp_folder,
        output_file=args.output
    )


def cmd_orders(args: argparse.Namespace) -> None:
    """Handle orders migration command."""
    tool = OrderMigrationTool()
    tool.convert_orders(
        input_file=args.input,
        output_file=args.output,
        meta_mapping_file=args.meta_mapping
    )


def cmd_collections(args: argparse.Namespace) -> None:
    """Handle collections/categories migration command."""
    config = {
        'use_smart_collections': not args.manual_collections,
        'image_mapping_file': args.image_mapping
    }
    tool = CollectionMigrationTool(config)
    tool.convert_collections(
        input_file=args.input,
        output_file=args.output,
        image_mapping_file=args.image_mapping
    )


def cmd_reviews(args: argparse.Namespace) -> None:
    """Handle reviews migration command."""
    tool = ReviewMigrationTool()
    tool.convert_reviews(
        input_file=args.input,
        output_file=args.output,
        product_mapping_file=args.product_mapping
    )


def cmd_discounts(args: argparse.Namespace) -> None:
    """Handle discounts/promocodes migration command."""
    config = {
        'default_minimum_amount': args.min_amount,
        'default_usage_limit': None,
        'batch_size': 500
    }
    tool = DiscountMigrationTool(config)
    tool.convert_discounts(
        input_file=args.input,
        output_file=args.output,
        product_mapping_file=args.product_mapping
    )


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='woo-to-sp',
        description='WooCommerce to Shopify Migration Toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s products -i woo_products.csv -o shopify_products.csv
  %(prog)s customers -w woo_customers.csv -m mailchimp_data.zip -o shopify_customers.csv
  %(prog)s orders -i woo_orders.csv -o shopify_orders.csv
  %(prog)s collections -i woo_categories.csv -o shopify_collections.csv
  %(prog)s reviews -i woo_reviews.csv -o shopify_reviews.csv
  %(prog)s discounts -i woo_coupons.csv -o shopify_discounts.csv
'''
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    subparsers = parser.add_subparsers(dest='command', help='Migration commands')

    # Products subcommand
    products_parser = subparsers.add_parser('products', help='Migrate products')
    products_parser.add_argument('-i', '--input', required=True, help='WooCommerce products CSV')
    products_parser.add_argument('-o', '--output', required=True, help='Shopify products CSV')
    products_parser.add_argument('-m', '--image-mapping', help='Image mapping CSV (optional)')
    products_parser.add_argument('--skip-drafts', action='store_true', help='Skip draft products')
    products_parser.add_argument('--no-images', action='store_true', help='Disable image migration')
    products_parser.set_defaults(func=cmd_products)

    # Customers subcommand
    customers_parser = subparsers.add_parser('customers', help='Migrate customers')
    customers_parser.add_argument('-w', '--woo-file', help='WooCommerce customers CSV')
    customers_parser.add_argument('-m', '--mailchimp-folder', help='MailChimp export folder/zip')
    customers_parser.add_argument('-o', '--output', required=True, help='Shopify customers CSV')
    customers_parser.set_defaults(func=cmd_customers)

    # Orders subcommand
    orders_parser = subparsers.add_parser('orders', help='Migrate orders')
    orders_parser.add_argument('-i', '--input', required=True, help='WooCommerce orders CSV')
    orders_parser.add_argument('-o', '--output', required=True, help='Shopify orders CSV')
    orders_parser.add_argument('-m', '--meta-mapping', help='Meta mapping CSV (optional)')
    orders_parser.set_defaults(func=cmd_orders)

    # Collections subcommand
    collections_parser = subparsers.add_parser('collections', help='Migrate categories/collections')
    collections_parser.add_argument('-i', '--input', required=True, help='WooCommerce categories CSV')
    collections_parser.add_argument('-o', '--output', required=True, help='Shopify collections CSV')
    collections_parser.add_argument('-m', '--image-mapping', help='Image mapping CSV (optional)')
    collections_parser.add_argument('--manual-collections', action='store_true', help='Use manual collections')
    collections_parser.set_defaults(func=cmd_collections)

    # Reviews subcommand
    reviews_parser = subparsers.add_parser('reviews', help='Migrate product reviews')
    reviews_parser.add_argument('-i', '--input', required=True, help='WooCommerce reviews CSV')
    reviews_parser.add_argument('-o', '--output', required=True, help='Shopify reviews CSV')
    reviews_parser.add_argument('-m', '--product-mapping', help='Product mapping CSV (optional)')
    reviews_parser.set_defaults(func=cmd_reviews)

    # Discounts subcommand
    discounts_parser = subparsers.add_parser('discounts', help='Migrate coupons/discount codes')
    discounts_parser.add_argument('-i', '--input', required=True, help='WooCommerce coupons CSV')
    discounts_parser.add_argument('-o', '--output', required=True, help='Shopify discounts CSV')
    discounts_parser.add_argument('-m', '--product-mapping', help='Product mapping CSV (optional)')
    discounts_parser.add_argument('--min-amount', type=float, default=0, help='Default minimum amount')
    discounts_parser.set_defaults(func=cmd_discounts)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.verbose)

    try:
        args.func(args)
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
