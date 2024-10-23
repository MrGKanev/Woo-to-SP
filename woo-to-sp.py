import pandas as pd
import json
from datetime import datetime
import re

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

def parse_address(address_str):
    """Parse address string into components."""
    try:
        if isinstance(address_str, str) and (address_str.startswith('{') or address_str.startswith('[')):
            return json.loads(address_str)
        return address_str
    except:
        return address_str

def parse_variation_attributes(variation_data):
    """
    Parse variation attributes into Shopify format.
    
    Args:
        variation_data (dict): WooCommerce variation data
        
    Returns:
        tuple: (variant_title, variant_options)
    """
    if not variation_data:
        return '', {}
    
    try:
        attributes = {}
        title_parts = []
        
        # Handle different variation formats from WooCommerce
        if isinstance(variation_data, str):
            # Try to parse JSON string
            variation_data = json.loads(variation_data)
            
        if isinstance(variation_data, dict):
            # Handle direct attribute dictionary
            attributes = variation_data
        elif isinstance(variation_data, list):
            # Handle attribute list format
            for attr in variation_data:
                if isinstance(attr, dict):
                    name = attr.get('name', '').replace('attribute_pa_', '').replace('attribute_', '')
                    value = attr.get('value', '')
                    attributes[name] = value
                    title_parts.append(f"{value}")
        
        # Clean up attribute names and values
        cleaned_attributes = {}
        for key, value in attributes.items():
            # Remove common WooCommerce prefixes
            clean_key = key.replace('attribute_pa_', '').replace('attribute_', '')
            clean_key = clean_key.title()  # Capitalize first letter
            cleaned_attributes[clean_key] = value
            title_parts.append(f"{value}")
        
        # Create variant title
        variant_title = ' / '.join(filter(None, title_parts))
        
        return variant_title, cleaned_attributes
        
    except Exception as e:
        print(f"Error parsing variation attributes: {str(e)}")
        return '', {}

def convert_woo_to_shopify(input_file, output_file):
    """
    Convert WooCommerce order export CSV to Shopify-compatible format.
    
    Args:
        input_file (str): Path to WooCommerce export CSV file
        output_file (str): Path to save Shopify-compatible CSV file
    """
    try:
        # Read WooCommerce export file
        df = pd.read_csv(input_file)
        
        # Create Shopify formatted dataframe
        shopify_orders = []
        
        for _, row in df.iterrows():
            # Parse basic order info
            order_data = {
                'Name': f'#{row["Order Number"]}',
                'Email': row['Customer Email'],
                'Financial Status': 'paid' if row['Order Status'] == 'completed' else 'pending',
                'Fulfillment Status': 'fulfilled' if row['Order Status'] == 'completed' else 'unfulfilled',
                'Currency': row.get('Currency', 'USD'),
                'Created at': pd.to_datetime(row['Order Date']).strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # Handle addresses
            billing_address = parse_address(row.get('Billing Address', {}))
            shipping_address = parse_address(row.get('Shipping Address', {}))
            
            # Billing address fields
            order_data.update({
                'Billing Name': f"{billing_address.get('first_name', '')} {billing_address.get('last_name', '')}".strip(),
                'Billing Street': billing_address.get('address_1', ''),
                'Billing Address2': billing_address.get('address_2', ''),
                'Billing Company': billing_address.get('company', ''),
                'Billing City': billing_address.get('city', ''),
                'Billing Province': billing_address.get('state', ''),
                'Billing Province Code': billing_address.get('state', ''),
                'Billing Zip': billing_address.get('postcode', ''),
                'Billing Country': billing_address.get('country', ''),
                'Billing Phone': clean_phone(billing_address.get('phone', ''))
            })
            
            # Shipping address fields
            order_data.update({
                'Shipping Name': f"{shipping_address.get('first_name', '')} {shipping_address.get('last_name', '')}".strip(),
                'Shipping Street': shipping_address.get('address_1', ''),
                'Shipping Address2': shipping_address.get('address_2', ''),
                'Shipping Company': shipping_address.get('company', ''),
                'Shipping City': shipping_address.get('city', ''),
                'Shipping Province': shipping_address.get('state', ''),
                'Shipping Province Code': shipping_address.get('state', ''),
                'Shipping Zip': shipping_address.get('postcode', ''),
                'Shipping Country': shipping_address.get('country', ''),
                'Shipping Phone': clean_phone(shipping_address.get('phone', ''))
            })
            
            # Parse line items if they exist
            if 'Line Items' in row:
                try:
                    line_items = json.loads(row['Line Items'])
                    for item in line_items:
                        item_data = {
                            'Lineitem name': item.get('name', ''),
                            'Lineitem quantity': item.get('quantity', 1),
                            'Lineitem price': item.get('price', 0),
                            'Lineitem sku': item.get('sku', ''),
                            'Lineitem requires shipping': 'true',
                            'Lineitem taxable': 'true',
                        }
                        
                        # Handle variations
                        variation_data = item.get('variation', item.get('variation_data', {}))
                        if variation_data:
                            variant_title, variant_options = parse_variation_attributes(variation_data)
                            
                            if variant_title:
                                item_data['Lineitem variant title'] = variant_title
                            
                            # Add variant options (up to 3, as per Shopify's limit)
                            for i, (option_name, option_value) in enumerate(variant_options.items(), 1):
                                if i <= 3:  # Shopify supports up to 3 options
                                    item_data[f'Lineitem option{i} name'] = option_name
                                    item_data[f'Lineitem option{i} value'] = option_value
                        
                        # Create a new order entry for each line item
                        new_order = order_data.copy()
                        new_order.update(item_data)
                        shopify_orders.append(new_order)
                except Exception as e:
                    print(f"Warning: Could not parse line items for order {row['Order Number']}: {str(e)}")
                    continue
            
            # Add taxes, shipping, and totals
            for order in shopify_orders:
                order.update({
                    'Taxes Included': 'false',
                    'Tax 1 Name': 'Tax',
                    'Tax 1 Value': row.get('Total Tax', 0),
                    'Shipping Line Title': row.get('Shipping Method', 'Standard'),
                    'Shipping Line Price': row.get('Shipping Total', 0),
                    'Total': row.get('Order Total', 0),
                })
        
        # Convert to DataFrame and save
        shopify_df = pd.DataFrame(shopify_orders)
        shopify_df.to_csv(output_file, index=False)
        
        print(f"Successfully converted {len(shopify_orders)} orders to Shopify format")
        print(f"Output saved to: {output_file}")
        
    except Exception as e:
        print(f"Error converting orders: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage
    input_file = "woocommerce_orders_export.csv"
    output_file = "shopify_orders_import.csv"
    convert_woo_to_shopify(input_file, output_file)