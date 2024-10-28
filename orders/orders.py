# orders/orders.py
import pandas as pd
import json
from datetime import datetime
import re
from pathlib import Path
from typing import Dict, List, Optional
import logging
import sys

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from configs.zerno_config import get_transform_config
from configs.country_codes import get_country_code

class OrderMigrationTool:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.setup_logging()
        self.stats = {
            'total_orders': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'line_items_created': 0
        }
        self.transform_config = get_transform_config()
        
    def setup_logging(self):
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

    def clean_phone(self, phone: str) -> str:
        """Clean phone numbers to match Shopify format."""
        if pd.isna(phone) or not phone:
            return ''
        # Remove all non-numeric characters
        phone = re.sub(r'[^\d+]', '', str(phone))
        # Ensure it starts with + for international format if needed
        if not phone.startswith('+'):
            # Assume US/Canada number if no country code
            if len(phone) == 10:
                phone = '+1' + phone
        return phone

    def clean_address_field(self, value: str) -> str:
        """Clean and validate address field, return 'Not Provided' if empty."""
        if pd.isna(value) or not str(value).strip():
            return 'Not Provided'
        return str(value).strip()

    def parse_meta_info(self, meta_str: str, original_price: float) -> List[Dict]:
        """Parse meta information and create separate line items as needed."""
        meta_items = []
        
        if not meta_str or pd.isna(meta_str):
            return meta_items
            
        # Extract all meta fields
        meta_matches = re.finditer(r'meta:([^:]+):([^|]+)', meta_str)
        base_name = re.search(r'name:([^|]+)', meta_str)
        base_product_name = base_name.group(1) if base_name else "Product"
        
        # Group meta fields by type
        variant_metas = {}
        component_items = []
        
        for match in meta_matches:
            meta_key = match.group(1)
            meta_value = match.group(2).strip()
            
            if self.transform_config.should_keep_variant(meta_key):
                # Store as variant attribute
                variant_metas[meta_key] = meta_value
            else:
                # Create separate line item
                component = self.transform_config.extract_meta_items(f"meta:{meta_key}:{meta_value}")
                if component:
                    component_items.extend(component)

        # Create main product with variants
        variant_description = []
        for key, value in variant_metas.items():
            clean_key = key.replace('pa_', '').replace('-', ' ').title()
            variant_description.append(f"{clean_key}: {value.replace('-', ' ').title()}")
        
        main_item = {
            'name': base_product_name,
            'variant_info': ' - '.join(variant_description) if variant_description else '',
            'price': original_price,
            'requires_shipping': True,
            'taxable': True,
            'is_main_item': True
        }
        meta_items.append(main_item)
        
        # Add component items
        for item in component_items:
            # Set price to 0 since it's included in main item price
            item['price'] = 0
            meta_items.append(item)
        
        # Process any additional add-ons
        addon_items = self.transform_config.process_addons(meta_str)
        meta_items.extend(addon_items)
        
        return meta_items

    def convert_orders(self, input_file: str, output_file: str):
        """Convert WooCommerce orders to Shopify format."""
        try:
            self.logger.info(f"Starting order migration from {input_file}")
            
            # Read WooCommerce orders
            df = pd.read_csv(input_file)
            self.stats['total_orders'] = len(df)
            
            shopify_orders = []
            
            for _, order in df.iterrows():
                try:
                    # Clean and validate names
                    billing_first = self.clean_address_field(order.get('billing_first_name', ''))
                    billing_last = self.clean_address_field(order.get('billing_last_name', ''))
                    shipping_first = self.clean_address_field(order.get('shipping_first_name', ''))
                    shipping_last = self.clean_address_field(order.get('shipping_last_name', ''))

                    # Base order data with validated addresses
                    order_data = {
                        'Name': f'#{order["order_number"]}',
                        'Email': order.get('customer_email', ''),
                        'Financial Status': 'paid' if order.get('status') == 'completed' else 'pending',
                        'Fulfillment Status': 'fulfilled' if order.get('status') == 'completed' else 'unfulfilled',
                        'Currency': order.get('order_currency', 'USD'),
                        'Created at': pd.to_datetime(order['order_date']).strftime('%Y-%m-%d %H:%M:%S'),
                        
                        # Billing address fields
                        'Billing Name': f"{billing_first} {billing_last}".strip(),
                        'Billing Street': self.clean_address_field(order.get('billing_address_1')),
                        'Billing Address2': self.clean_address_field(order.get('billing_address_2', '')),
                        'Billing Company': self.clean_address_field(order.get('billing_company', '')),
                        'Billing City': self.clean_address_field(order.get('billing_city')),
                        'Billing Province': self.clean_address_field(order.get('billing_state', '')),
                        'Billing Province Code': self.clean_address_field(order.get('billing_state', '')),
                        'Billing Zip': self.clean_address_field(order.get('billing_postcode', '')),
                        'Billing Country': get_country_code(order.get('billing_country', '')),  # Using external country code lookup
                        'Billing Phone': self.clean_phone(order.get('billing_phone', '')),
                        
                        # Shipping address fields
                        'Shipping Name': f"{shipping_first} {shipping_last}".strip(),
                        'Shipping Street': self.clean_address_field(order.get('shipping_address_1')),
                        'Shipping Address2': self.clean_address_field(order.get('shipping_address_2', '')),
                        'Shipping Company': self.clean_address_field(order.get('shipping_company', '')),
                        'Shipping City': self.clean_address_field(order.get('shipping_city')),
                        'Shipping Province': self.clean_address_field(order.get('shipping_state', '')),
                        'Shipping Province Code': self.clean_address_field(order.get('shipping_state', '')),
                        'Shipping Zip': self.clean_address_field(order.get('shipping_postcode', '')),
                        'Shipping Country': get_country_code(order.get('shipping_country', '')),  # Using external country code lookup
                        'Shipping Phone': self.clean_phone(order.get('shipping_phone', ''))
                    }
                    
                    # If shipping address is empty, copy from billing
                    if order_data['Shipping Street'] == 'Not Provided':
                        for field in ['Name', 'Street', 'Address2', 'Company', 'City', 'Province', 
                                    'Province Code', 'Zip', 'Country', 'Phone']:
                            order_data[f'Shipping {field}'] = order_data[f'Billing {field}']
                    
                    # Process line items
                    for i in range(1, 20):  # Assuming max 19 line items
                        line_item_key = f'line_item_{i}'
                        if line_item_key in order and not pd.isna(order[line_item_key]):
                            line_item = str(order[line_item_key])
                            
                            # Get original price
                            total_match = re.search(r'total:(\d+\.?\d*)', line_item)
                            original_price = float(total_match.group(1)) if total_match else 0
                            
                            # Parse meta info and create line items
                            items = self.parse_meta_info(line_item, original_price)
                            
                            # Create Shopify order entries for each item
                            for idx, item in enumerate(items):
                                item_order = order_data.copy()
                                
                                # Add variant info to name if present
                                display_name = item['name']
                                if 'variant_info' in item and item['variant_info']:
                                    display_name += f" ({item['variant_info']})"
                                
                                item_order.update({
                                    'Lineitem name': display_name,
                                    'Lineitem quantity': item.get('quantity', 1),
                                    'Lineitem price': item['price'],
                                    'Lineitem sku': item.get('sku', ''),
                                    'Lineitem requires shipping': 'true' if item.get('requires_shipping', True) else 'false',
                                    'Lineitem taxable': 'true' if item.get('taxable', True) else 'false',
                                })
                                
                                # Add totals only to first/main item
                                if item.get('is_main_item', False):
                                    item_order.update({
                                        'Taxes Included': 'false',
                                        'Tax 1 Name': 'Tax',
                                        'Tax 1 Value': order.get('tax_total', 0),
                                        'Shipping Line Title': order.get('shipping_method', 'Standard'),
                                        'Shipping Line Price': order.get('shipping_total', 0),
                                        'Total': order.get('order_total', 0),
                                    })
                                
                                shopify_orders.append(item_order)
                                self.stats['line_items_created'] += 1
                    
                    self.stats['successful'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing order {order.get('order_number')}: {str(e)}")
                    self.stats['failed'] += 1
            
            # Save to CSV
            if shopify_orders:
                output_df = pd.DataFrame(shopify_orders)
                output_df.to_csv(output_file, index=False)
                
                # Generate report
                self.generate_report(output_file)
                
                self.logger.info(f"Order migration completed. See {output_file} for results.")
            else:
                self.logger.warning("No orders were successfully processed!")
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

    def generate_report(self, output_file: str) -> None:
        """Generate migration report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'input_file': self.config.get('input_file', 'N/A'),
            'output_file': output_file,
            'statistics': self.stats,
            'success_rate': f"{(self.stats['successful'] / self.stats['total_orders'] * 100):.2f}%"
        }
        
        # Save report
        report_file = Path('reports') / f'order_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Migration report saved to {report_file}")

def main():
    """Example usage of the OrderMigrationTool."""
    # Use current directory
    current_dir = Path.cwd()
    
    # Default file names
    input_file = current_dir / "orders/woocommerce_orders_export.csv"
    output_file = current_dir / "orders/shopify_orders_import.csv"
    
    tool = OrderMigrationTool()
    
    try:
        tool.convert_orders(
            input_file=str(input_file),
            output_file=str(output_file)
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()