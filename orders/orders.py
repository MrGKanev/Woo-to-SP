# orders/orders.py
import pandas as pd
import json
from datetime import datetime
import re
from pathlib import Path

def load_meta_mapping(mapping_file):
    """
    Load meta mapping configuration from CSV file.
    Returns empty dict if file doesn't exist.
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
            return mapping
        else:
            print(f"Warning: Meta mapping file {mapping_file} not found. Using default mapping.")
            return {}
    except Exception as e:
        print(f"Error loading meta mapping: {str(e)}")
        return {}

def format_meta_name(key: str, value: str, mapping: dict) -> str:
    """Format meta item name based on mapping configuration."""
    if key in mapping:
        prefix = mapping[key]['name_prefix']
        suffix = mapping[key]['name_suffix']
        
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

def clean_phone(phone):
    """Clean phone numbers to match Shopify format."""
    if pd.isna(phone):
        return ''
    # Remove all non-numeric characters
    phone = re.sub(r'[^\d+]', '', str(phone))
    # Ensure it starts with + for international format if needed
    if not phone.startswith('+'):
        # Assume US/Canada number if no country code
        if len(phone) == 10:
            phone = '+1' + phone
    return phone

def parse_meta_info(meta_str, meta_mapping):
    """Parse meta information from WooCommerce order item."""
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
    prices = {}
    pao_match = re.search(r'meta:_pao_ids:([^|]+)', meta_str)
    if pao_match:
        pao_data = pao_match.group(1)
        price_matches = re.finditer(r's:3:"key";s:\d+:"([^"]+)";s:5:"value";s:\d+:"([^"]+)";.*?s:9:"raw_price";d:(\d+)', pao_data)
        for match in price_matches:
            key, value, price = match.groups()
            prices[key] = float(price)
    
    # Create product items from meta
    for key, value in meta_values.items():
        if key in meta_mapping:
            # Skip if it's a variant attribute
            if key.startswith('pa_'):
                continue
                
            # Format item name using mapping
            item_name = format_meta_name(key, value, meta_mapping)
                
            # Generate SKU
            sku_prefix = meta_mapping[key]['sku_prefix']
            sku = f"{sku_prefix}{value.lower().replace(' ', '-')}"
            
            item_data = {
                'name': item_name,
                'quantity': 1,
                'price': prices.get(key, 0),  # Get price from _pao_ids if available
                'sku': sku,
                'requires_shipping': True,
                'taxable': True
            }
            
            meta_items.append(item_data)
    
    return meta_items

def convert_woo_to_shopify(input_file, output_file, meta_mapping_file='meta_mapping.csv'):
    """
    Convert WooCommerce order export CSV to Shopify-compatible format.
    
    Args:
        input_file (str): Path to WooCommerce export CSV file
        output_file (str): Path to save Shopify-compatible CSV file
        meta_mapping_file (str): Path to meta mapping configuration CSV file
    """
    try:
        # Load meta mapping configuration
        meta_mapping = load_meta_mapping(meta_mapping_file)
        
        # Read WooCommerce export file
        df = pd.read_csv(input_file)
        
        # Create Shopify formatted dataframe
        shopify_orders = []
        
        for _, row in df.iterrows():
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
                'Billing Address2': row['billing_address_2'],
                'Billing Company': row['billing_company'],
                'Billing City': row['billing_city'],
                'Billing Province': row['billing_state'],
                'Billing Province Code': row['billing_state'],
                'Billing Zip': row['billing_postcode'],
                'Billing Country': row['billing_country'],
                'Billing Phone': clean_phone(row['billing_phone']),
                'Shipping Name': f"{row['shipping_first_name']} {row['shipping_last_name']}".strip(),
                'Shipping Street': row['shipping_address_1'],
                'Shipping Address2': row['shipping_address_2'],
                'Shipping Company': row['shipping_company'],
                'Shipping City': row['shipping_city'],
                'Shipping Province': row['shipping_state'],
                'Shipping Province Code': row['shipping_state'],
                'Shipping Zip': row['shipping_postcode'],
                'Shipping Country': row['shipping_country'],
                'Shipping Phone': clean_phone(row['shipping_phone'])
            }
            
            # Process all possible line items
            order_items = []
            
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
                            'price': total / quantity,
                            'sku': sku_match.group(1).strip() if sku_match else '',
                            'requires_shipping': True,
                            'taxable': True
                        }
                        order_items.append(main_item)
                        
                        # Parse and add meta items as separate products
                        meta_items = parse_meta_info(line_item, meta_mapping)
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
        
        # Convert to DataFrame and save
        shopify_df = pd.DataFrame(shopify_orders)
        shopify_df.to_csv(output_file, index=False)
        
        print(f"Successfully converted {len(df)} orders with meta items to Shopify format")
        print(f"Total line items created: {len(shopify_orders)}")
        print(f"Output saved to: {output_file}")
        
    except Exception as e:
        print(f"Error converting orders: {str(e)}")
        raise

if __name__ == "__main__":
    
    # You can change these file paths directly here
    input_file = "woocommerce_orders_export.csv"     # Change this to your WooCommerce export file
    output_file = "shopify_orders_import.csv"        # Change this to your desired output file
    meta_mapping_file = "meta_mapping.csv"           # Change this to your meta mapping file
    
    convert_woo_to_shopify(input_file, output_file, meta_mapping_file)