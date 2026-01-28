# promocodes/promocode.py
"""Discount codes migration module for converting WooCommerce coupons to Shopify discount codes."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
import argparse
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from base.base_migration import BaseMigrationTool


class DiscountMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce coupons to Shopify discount codes."""

    TOOL_NAME = "discount"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize discount migration tool."""
        super().__init__(config)
        self.product_mapping: Dict[str, str] = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for discount migration."""
        config = super()._get_default_config()
        config.update({
            'default_minimum_amount': 0,
            'default_usage_limit': None,
            'max_code_length': 50,
        })
        return config

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics for discount migration."""
        stats = super()._init_stats()
        stats.update({
            'percentage_discounts': 0,
            'fixed_discounts': 0,
            'codes_truncated': 0,
        })
        return stats

    def validate_item(self, coupon: Any) -> Tuple[bool, List[str]]:
        """
        Validate coupon data before conversion.

        Args:
            coupon: Coupon data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check for code
        if not coupon.get('code'):
            errors.append("Missing discount code")

        # Check for amount
        try:
            amount = float(coupon.get('amount', 0))
            if amount < 0:
                errors.append("Discount amount cannot be negative")
        except (ValueError, TypeError):
            errors.append("Invalid discount amount")

        return len(errors) == 0, errors

    def clean_discount_code(self, code: str) -> str:
        """
        Clean and validate discount code.

        Args:
            code: Discount code to clean

        Returns:
            Cleaned discount code
        """
        if not code:
            return ""

        # Remove special characters and spaces, uppercase
        code = re.sub(r'[^A-Z0-9_-]', '', str(code).upper())

        # Truncate if needed
        max_length = self.config.get('max_code_length', 50)
        if len(code) > max_length:
            code = code[:max_length]
            self.stats['codes_truncated'] += 1

        return code

    def convert_amount_type(self, woo_type: str, amount: float) -> Tuple[str, float]:
        """
        Convert WooCommerce discount type to Shopify format.

        Args:
            woo_type: WooCommerce discount type
            amount: Discount amount

        Returns:
            Tuple of (shopify_type, amount)
        """
        if woo_type == 'percent':
            self.stats['percentage_discounts'] += 1
            return 'percentage', amount
        elif woo_type in ['fixed_cart', 'fixed_product']:
            self.stats['fixed_discounts'] += 1
            return 'fixed_amount', amount
        else:
            self.stats['percentage_discounts'] += 1
            return 'percentage', amount  # Default to percentage

    def process_product_restrictions(
        self,
        included_products: str,
        excluded_products: str
    ) -> Dict[str, List[str]]:
        """
        Process product restrictions for Shopify format.

        Args:
            included_products: Comma-separated list of included product IDs
            excluded_products: Comma-separated list of excluded product IDs

        Returns:
            Dictionary with entitled and excluded product IDs
        """
        restrictions = {
            'entitled_product_ids': [],
            'excluded_product_ids': []
        }

        if included_products and not pd.isna(included_products):
            restrictions['entitled_product_ids'] = [
                str(pid).strip() for pid in str(included_products).split(',')
                if pid.strip()
            ]

        if excluded_products and not pd.isna(excluded_products):
            restrictions['excluded_product_ids'] = [
                str(pid).strip() for pid in str(excluded_products).split(',')
                if pid.strip()
            ]

        return restrictions

    def convert_item(self, coupon: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a WooCommerce coupon to Shopify discount code format.

        Args:
            coupon: Coupon data to convert

        Returns:
            Converted discount code data for Shopify
        """
        # Clean and validate discount code
        code = self.clean_discount_code(coupon['code'])
        if not code:
            self.logger.warning(f"Invalid coupon code after cleaning: {coupon['code']}")
            return None

        # Convert discount type and amount
        discount_type, amount = self.convert_amount_type(
            coupon.get('discount_type', 'percent'),
            float(coupon.get('amount', 0))
        )

        # Process product restrictions
        restrictions = self.process_product_restrictions(
            coupon.get('product_ids', ''),
            coupon.get('exclude_product_ids', '')
        )

        # Create Shopify discount
        return {
            'Discount Code': code,
            'Type': discount_type,
            'Amount': amount,
            'Minimum Purchase Amount': coupon.get(
                'minimum_amount',
                self.config['default_minimum_amount']
            ),
            'Starts At': self.format_date(coupon.get('date_created', '')),
            'Ends At': self.format_date(coupon.get('date_expires', '')),
            'Usage Limit': coupon.get('usage_limit', self.config['default_usage_limit']),
            'Once Per Customer': str(coupon.get('individual_use', 'no')).lower() == 'yes',
            'Status': 'enabled' if str(coupon.get('enabled', 'yes')).lower() == 'yes' else 'disabled',
            'Applies To': 'all' if not restrictions['entitled_product_ids'] else 'specific',
            'Products': ','.join(restrictions['entitled_product_ids']),
            'Excluded Products': ','.join(restrictions['excluded_product_ids']),
            'Description': self.clean_text(coupon.get('description', '')),
            'Times Used': int(coupon.get('usage_count', 0) or 0)
        }

    def convert_discounts(
        self,
        input_file: str,
        output_file: str,
        product_mapping_file: Optional[str] = None
    ) -> None:
        """
        Convert WooCommerce coupons to Shopify discount codes.

        Args:
            input_file: Path to WooCommerce coupons export CSV
            output_file: Path to save Shopify discount codes CSV
            product_mapping_file: Optional CSV mapping WooCommerce product IDs to Shopify IDs
        """
        # Load product mapping if provided
        if product_mapping_file and Path(product_mapping_file).exists():
            mapping_df = pd.read_csv(product_mapping_file)
            self.product_mapping = self.load_mapping(mapping_df)
            self.logger.info(f"Loaded {len(self.product_mapping)} product mappings")

        # Use base class conversion
        self.convert_data(input_file, output_file)

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """
        Load product ID mapping.

        Args:
            mapping_df: DataFrame with woo_id and shopify_id columns

        Returns:
            Dictionary mapping WooCommerce IDs to Shopify IDs
        """
        if 'woo_id' in mapping_df.columns and 'shopify_id' in mapping_df.columns:
            return dict(zip(
                mapping_df['woo_id'].astype(str),
                mapping_df['shopify_id'].astype(str)
            ))
        return {}


def main():
    """CLI entry point for discount code migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce coupons to Shopify discount codes'
    )
    parser.add_argument(
        '-i', '--input',
        default='wp_coupons_export.csv',
        help='Path to WooCommerce coupons export CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_discounts_import.csv',
        help='Path to save Shopify discount codes CSV'
    )
    parser.add_argument(
        '-m', '--product-mapping',
        default=None,
        help='Path to product mapping CSV (optional)'
    )
    parser.add_argument(
        '--min-amount',
        type=float,
        default=0,
        help='Default minimum purchase amount'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    config = {
        'default_minimum_amount': args.min_amount,
        'show_progress': not args.no_progress,
    }

    tool = DiscountMigrationTool(config)

    try:
        tool.convert_discounts(
            input_file=args.input,
            output_file=args.output,
            product_mapping_file=args.product_mapping
        )
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
