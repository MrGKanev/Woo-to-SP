# orders/orders.py
"""Order migration module for converting WooCommerce orders to Shopify format."""

import pandas as pd
import json
from datetime import datetime
import re
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any
import argparse


class OrderMigrationTool:
    """Tool for migrating WooCommerce orders to Shopify format."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize migration tool with configuration.

        Args:
            config: Configuration dictionary with options like meta_mapping_file
        """
        self.config = config or {}
        self.meta_mapping: Dict[str, Dict[str, str]] = {}
        self.setup_logging()
        self.stats = {
            'total_orders': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'line_items_created': 0
        }

    def setup_logging(self) -> None:
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f'order_migration_{datetime.now():%Y%m%d_%H%M%S}.log'

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

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
                self.logger.info(f"Loaded {len(mapping)} meta mappings from {mapping_file}")
                return mapping
            else:
                self.logger.warning(f"Meta mapping file {mapping_file} not found. Using default mapping.")
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

            # Handle special case where value should be prefix to suffix
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

    @staticmethod
    def clean_phone(phone: Any) -> str:
        """
        Clean phone numbers to match Shopify format.

        Args:
            phone: Phone number to clean

        Returns:
            Cleaned phone number string
        """
        if pd.isna(phone) or not phone:
            return ''
        # Remove all non-numeric characters except +
        phone = re.sub(r'[^\d+]', '', str(phone))
        # Ensure it starts with + for international format if needed
        if not phone.startswith('+'):
            # Assume US/Canada number if no country code
            if len(phone) == 10:
                phone = '+1' + phone
        return phone

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

        # First pass: collect all meta values
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
                # Skip if it's a variant attribute
                if key.startswith('pa_'):
                    continue

                # Format item name using mapping
                item_name = self.format_meta_name(key, value)

                # Generate SKU
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

        return meta_items

    def convert_orders(
        self,
        input_file: str,
        output_file: str,
        meta_mapping_file: Optional[str] = None
    ) -> None:
        """
        Convert WooCommerce order export CSV to Shopify-compatible format.

        Args:
            input_file: Path to WooCommerce export CSV file
            output_file: Path to save Shopify-compatible CSV file
            meta_mapping_file: Path to meta mapping configuration CSV file
        """
        try:
            self.logger.info(f"Starting order migration from {input_file}")

            # Load meta mapping configuration
            if meta_mapping_file:
                self.meta_mapping = self.load_meta_mapping(meta_mapping_file)

            # Read WooCommerce export file
            df = pd.read_csv(input_file)
            self.stats['total_orders'] = len(df)

            # Create Shopify formatted dataframe
            shopify_orders = []

            for _, row in df.iterrows():
                try:
                    # Base order data
                    order_data = {
                        'Name': f'#{row["order_number"]}',
                        'Email': row['customer_email'],
                        'Financial Status': 'paid' if row['status'] == 'completed' else 'pending',
                        'Fulfillment Status': 'fulfilled' if row['status'] == 'completed' else 'unfulfilled',
                        'Currency': row.get('order_currency', 'USD'),
                        'Created at': pd.to_datetime(row['order_date']).strftime('%Y-%m-%d %H:%M:%S'),
                        'Billing Name': f"{row['billing_first_name']} {row['billing_last_name']}".strip(),
                        'Billing Street': row['billing_address_1'],
                        'Billing Address2': row.get('billing_address_2', ''),
                        'Billing Company': row.get('billing_company', ''),
                        'Billing City': row['billing_city'],
                        'Billing Province': row['billing_state'],
                        'Billing Province Code': row['billing_state'],
                        'Billing Zip': row['billing_postcode'],
                        'Billing Country': row['billing_country'],
                        'Billing Phone': self.clean_phone(row.get('billing_phone', '')),
                        'Shipping Name': f"{row.get('shipping_first_name', '')} {row.get('shipping_last_name', '')}".strip(),
                        'Shipping Street': row.get('shipping_address_1', ''),
                        'Shipping Address2': row.get('shipping_address_2', ''),
                        'Shipping Company': row.get('shipping_company', ''),
                        'Shipping City': row.get('shipping_city', ''),
                        'Shipping Province': row.get('shipping_state', ''),
                        'Shipping Province Code': row.get('shipping_state', ''),
                        'Shipping Zip': row.get('shipping_postcode', ''),
                        'Shipping Country': row.get('shipping_country', ''),
                        'Shipping Phone': self.clean_phone(row.get('shipping_phone', ''))
                    }

                    # Process all possible line items
                    order_items: List[Dict[str, Any]] = []

                    # Process main line items
                    for i in range(1, 20):
                        line_item_key = f'line_item_{i}'
                        if line_item_key in row and not pd.isna(row[line_item_key]):
                            line_item = str(row[line_item_key])

                            # Extract main product info
                            name_match = re.search(r'name:([^|]+)', line_item)
                            qty_match = re.search(r'quantity:(\d+)', line_item)
                            total_match = re.search(r'total:(\d+\.?\d*)', line_item)
                            sku_match = re.search(r'sku:([^|]+)', line_item)

                            if name_match and qty_match and total_match:
                                quantity = int(qty_match.group(1))
                                total = float(total_match.group(1))

                                # Add main product
                                main_item = {
                                    'name': name_match.group(1).strip(),
                                    'quantity': quantity,
                                    'price': total / quantity if quantity > 0 else 0,
                                    'sku': sku_match.group(1).strip() if sku_match else '',
                                    'requires_shipping': True,
                                    'taxable': True
                                }
                                order_items.append(main_item)

                                # Parse and add meta items as separate products
                                meta_items = self.parse_meta_info(line_item)
                                order_items.extend(meta_items)

                    # Create separate Shopify order entries for each item
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
                                'Tax 1 Value': row.get('tax_total', 0),
                                'Shipping Line Title': row.get('shipping_method', 'Standard'),
                                'Shipping Line Price': row.get('shipping_total', 0),
                                'Total': row.get('order_total', 0),
                            })

                        shopify_orders.append(item_order)
                        self.stats['line_items_created'] += 1

                    self.stats['successful'] += 1

                except Exception as e:
                    self.logger.error(f"Error processing order {row.get('order_number', 'unknown')}: {str(e)}")
                    self.stats['failed'] += 1

            # Convert to DataFrame and save
            if shopify_orders:
                shopify_df = pd.DataFrame(shopify_orders)
                shopify_df.to_csv(output_file, index=False)

                # Generate report
                self.generate_report(output_file)

                self.logger.info(f"Order migration completed. See {output_file} for results.")
            else:
                self.logger.warning("No orders were successfully processed!")

        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

    def generate_report(self, output_file: str) -> None:
        """
        Generate migration report.

        Args:
            output_file: Path to the output file
        """
        total = max(self.stats['total_orders'], 1)
        report = {
            'timestamp': datetime.now().isoformat(),
            'input_file': self.config.get('input_file', 'N/A'),
            'output_file': output_file,
            'statistics': self.stats,
            'success_rate': f"{(self.stats['successful'] / total * 100):.2f}%",
            'configuration': self.config
        }

        # Save report
        report_file = Path('reports') / f'order_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Migration report saved to {report_file}")


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
        default='meta_mapping.csv',
        help='Path to meta mapping configuration CSV'
    )

    args = parser.parse_args()

    tool = OrderMigrationTool()

    try:
        tool.convert_orders(
            input_file=args.input,
            output_file=args.output,
            meta_mapping_file=args.meta_mapping
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
