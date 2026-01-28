# orders/orders.py
"""Order migration module for converting WooCommerce orders to Shopify format."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
import argparse
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from base.base_migration import BaseMigrationTool


class OrderMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce orders to Shopify format."""

    TOOL_NAME = "order"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize order migration tool."""
        super().__init__(config)
        self.meta_mapping: Dict[str, Dict[str, str]] = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for order migration."""
        config = super()._get_default_config()
        config.update({
            'max_line_items': 20,
            'default_currency': 'USD',
        })
        return config

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics for order migration."""
        stats = super()._init_stats()
        stats.update({
            'line_items_created': 0,
            'meta_items_created': 0,
        })
        return stats

    def validate_item(self, order: Any) -> Tuple[bool, List[str]]:
        """
        Validate order data before conversion.

        Args:
            order: Order data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not order.get('order_number'):
            errors.append("Missing order number")

        if not order.get('customer_email'):
            errors.append("Missing customer email")

        return len(errors) == 0, errors

    def load_meta_mapping(self, mapping_file: str) -> Dict[str, Dict[str, str]]:
        """
        Load meta mapping configuration from CSV file.

        Args:
            mapping_file: Path to the meta mapping CSV file

        Returns:
            Dictionary with meta key mappings
        """
        try:
            if Path(mapping_file).exists():
                df = pd.read_csv(mapping_file)
                mapping = {}
                for _, row in df.iterrows():
                    mapping[row['meta_key']] = {
                        'name_prefix': row['name_prefix'] if not pd.isna(row['name_prefix']) else '',
                        'name_suffix': row['name_suffix'] if not pd.isna(row['name_suffix']) else '',
                        'sku_prefix': row['sku_prefix'] if not pd.isna(row['sku_prefix']) else '',
                        'price_field': row['price_field'] if not pd.isna(row['price_field']) else ''
                    }
                self.logger.info(f"Loaded {len(mapping)} meta mappings")
                return mapping
            else:
                self.logger.warning(f"Meta mapping file {mapping_file} not found")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading meta mapping: {str(e)}")
            return {}

    def format_meta_name(self, key: str, value: str) -> str:
        """
        Format meta item name based on mapping configuration.

        Args:
            key: Meta key
            value: Meta value

        Returns:
            Formatted name string
        """
        if key in self.meta_mapping:
            prefix = self.meta_mapping[key]['name_prefix']
            suffix = self.meta_mapping[key]['name_suffix']

            if suffix and not prefix:
                return f"{value} {suffix}"

            name_parts = []
            if prefix:
                name_parts.append(prefix)
            name_parts.append(value)
            if suffix:
                name_parts.append(suffix)

            return " ".join(name_parts)
        return value

    def parse_meta_info(self, meta_str: str) -> List[Dict[str, Any]]:
        """
        Parse meta information from WooCommerce order item.

        Args:
            meta_str: Meta string from WooCommerce order

        Returns:
            List of parsed meta item dictionaries
        """
        meta_items = []

        if not meta_str or pd.isna(meta_str):
            return meta_items

        # Extract meta fields
        meta_pairs = re.findall(r'meta:([^:]+):([^|]+)', meta_str)

        # Collect all meta values
        meta_values = {}
        for key, value in meta_pairs:
            meta_values[key] = value.strip()

        # Extract prices from _pao_ids if present
        prices: Dict[str, float] = {}
        pao_match = re.search(r'meta:_pao_ids:([^|]+)', meta_str)
        if pao_match:
            pao_data = pao_match.group(1)
            price_matches = re.finditer(
                r's:3:"key";s:\d+:"([^"]+)";s:5:"value";s:\d+:"([^"]+)";.*?s:9:"raw_price";d:(\d+)',
                pao_data
            )
            for match in price_matches:
                key, value, price = match.groups()
                prices[key] = float(price)

        # Create product items from meta
        for key, value in meta_values.items():
            if key in self.meta_mapping:
                if key.startswith('pa_'):
                    continue

                item_name = self.format_meta_name(key, value)
                sku_prefix = self.meta_mapping[key]['sku_prefix']
                sku = f"{sku_prefix}{value.lower().replace(' ', '-')}"

                item_data = {
                    'name': item_name,
                    'quantity': 1,
                    'price': prices.get(key, 0),
                    'sku': sku,
                    'requires_shipping': True,
                    'taxable': True
                }

                meta_items.append(item_data)
                self.stats['meta_items_created'] += 1

        return meta_items

    def convert_item(self, order: Any) -> Optional[List[Dict[str, Any]]]:
        """
        Convert a WooCommerce order to Shopify format.
        Returns multiple rows (one per line item).

        Args:
            order: Order data to convert

        Returns:
            List of converted order line items for Shopify
        """
        # Base order data
        order_data = {
            'Name': f'#{order["order_number"]}',
            'Email': order['customer_email'],
            'Financial Status': 'paid' if order.get('status') == 'completed' else 'pending',
            'Fulfillment Status': 'fulfilled' if order.get('status') == 'completed' else 'unfulfilled',
            'Currency': order.get('order_currency', self.config['default_currency']),
            'Created at': self.format_date(order.get('order_date', '')),
            'Billing Name': f"{order.get('billing_first_name', '')} {order.get('billing_last_name', '')}".strip(),
            'Billing Street': order.get('billing_address_1', ''),
            'Billing Address2': order.get('billing_address_2', ''),
            'Billing Company': order.get('billing_company', ''),
            'Billing City': order.get('billing_city', ''),
            'Billing Province': order.get('billing_state', ''),
            'Billing Province Code': order.get('billing_state', ''),
            'Billing Zip': order.get('billing_postcode', ''),
            'Billing Country': order.get('billing_country', ''),
            'Billing Phone': self.clean_phone(order.get('billing_phone', '')),
            'Shipping Name': f"{order.get('shipping_first_name', '')} {order.get('shipping_last_name', '')}".strip(),
            'Shipping Street': order.get('shipping_address_1', ''),
            'Shipping Address2': order.get('shipping_address_2', ''),
            'Shipping Company': order.get('shipping_company', ''),
            'Shipping City': order.get('shipping_city', ''),
            'Shipping Province': order.get('shipping_state', ''),
            'Shipping Province Code': order.get('shipping_state', ''),
            'Shipping Zip': order.get('shipping_postcode', ''),
            'Shipping Country': order.get('shipping_country', ''),
            'Shipping Phone': self.clean_phone(order.get('shipping_phone', ''))
        }

        # Process all line items
        order_items: List[Dict[str, Any]] = []
        max_items = self.config.get('max_line_items', 20)

        for i in range(1, max_items + 1):
            line_item_key = f'line_item_{i}'
            if line_item_key not in order or pd.isna(order[line_item_key]):
                continue

            line_item = str(order[line_item_key])

            # Extract main product info
            name_match = re.search(r'name:([^|]+)', line_item)
            qty_match = re.search(r'quantity:(\d+)', line_item)
            total_match = re.search(r'total:(\d+\.?\d*)', line_item)
            sku_match = re.search(r'sku:([^|]+)', line_item)

            if name_match and qty_match and total_match:
                quantity = int(qty_match.group(1))
                total = float(total_match.group(1))

                main_item = {
                    'name': name_match.group(1).strip(),
                    'quantity': quantity,
                    'price': total / quantity if quantity > 0 else 0,
                    'sku': sku_match.group(1).strip() if sku_match else '',
                    'requires_shipping': True,
                    'taxable': True
                }
                order_items.append(main_item)
                self.stats['line_items_created'] += 1

                # Parse and add meta items
                meta_items = self.parse_meta_info(line_item)
                order_items.extend(meta_items)

        # Create Shopify order entries (one per line item)
        shopify_orders = []
        for idx, item in enumerate(order_items):
            item_order = order_data.copy()
            item_order.update({
                'Lineitem name': item['name'],
                'Lineitem quantity': item['quantity'],
                'Lineitem price': item['price'],
                'Lineitem sku': item['sku'],
                'Lineitem requires shipping': 'true' if item['requires_shipping'] else 'false',
                'Lineitem taxable': 'true' if item['taxable'] else 'false',
            })

            # Add totals only to first item
            if idx == 0:
                item_order.update({
                    'Taxes Included': 'false',
                    'Tax 1 Name': 'Tax',
                    'Tax 1 Value': order.get('tax_total', 0),
                    'Shipping Line Title': order.get('shipping_method', 'Standard'),
                    'Shipping Line Price': order.get('shipping_total', 0),
                    'Total': order.get('order_total', 0),
                })

            shopify_orders.append(item_order)

        return shopify_orders if shopify_orders else None

    def convert_orders(
        self,
        input_file: str,
        output_file: str,
        meta_mapping_file: Optional[str] = None
    ) -> None:
        """
        Convert WooCommerce orders to Shopify format.

        Args:
            input_file: Path to WooCommerce orders export CSV
            output_file: Path to save Shopify orders CSV
            meta_mapping_file: Path to meta mapping configuration CSV
        """
        # Load meta mapping if provided
        if meta_mapping_file:
            self.meta_mapping = self.load_meta_mapping(meta_mapping_file)

        # Use base class conversion
        self.convert_data(input_file, output_file)


def main():
    """CLI entry point for order migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce orders to Shopify format'
    )
    parser.add_argument(
        '-i', '--input',
        default='woocommerce_orders_export.csv',
        help='Path to WooCommerce orders export CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_orders_import.csv',
        help='Path to save Shopify orders CSV'
    )
    parser.add_argument(
        '-m', '--meta-mapping',
        default=None,
        help='Path to meta mapping configuration CSV'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    config = {
        'show_progress': not args.no_progress,
    }

    tool = OrderMigrationTool(config)

    try:
        tool.convert_orders(
            input_file=args.input,
            output_file=args.output,
            meta_mapping_file=args.meta_mapping
        )
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
