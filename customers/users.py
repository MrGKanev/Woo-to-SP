import pandas as pd
import json
from datetime import datetime
import re
from typing import Dict, List, Optional
import os
from pathlib import Path
import glob
import zipfile

class CustomerMigrationTool:
    def __init__(self):
        self.shopify_customers = []
        self.seen_emails = set()  # Track unique emails for deduplication
        self.mailchimp_data = {
            'subscribers': [],
            'merge_fields': {},
            'segments': {},
            'activities': {}
        }

    def clean_phone(self, phone: Optional[str]) -> str:
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

    def parse_address(self, address_str: str) -> Dict:
        """Parse address string into components."""
        try:
            if isinstance(address_str, str) and (address_str.startswith('{') or address_str.startswith('[')):
                return json.loads(address_str)
            return address_str if isinstance(address_str, dict) else {}
        except:
            return {}

    def parse_woo_customer(self, customer: pd.Series) -> Dict:
        """Convert WooCommerce customer data to Shopify format."""
        billing_address = self.parse_address(customer.get('Billing Address', {}))
        shipping_address = self.parse_address(customer.get('Shipping Address', {}))

        return {
            'Email': customer.get('Email', '').lower(),
            'First Name': customer.get('First Name', billing_address.get('first_name', '')),
            'Last Name': customer.get('Last Name', billing_address.get('last_name', '')),
            'Company': billing_address.get('company', ''),
            'Phone': self.clean_phone(billing_address.get('phone', '')),
            'Address1': billing_address.get('address_1', ''),
            'Address2': billing_address.get('address_2', ''),
            'City': billing_address.get('city', ''),
            'Province': billing_address.get('state', ''),
            'Province Code': billing_address.get('state', ''),
            'Country': billing_address.get('country', ''),
            'Zip': billing_address.get('postcode', ''),
            'Customer Type': 'regular',
            'Accepts Marketing': customer.get('Accepts Marketing', 'no').lower() in ['yes', 'true', '1'],
            'Tags': 'Woocommerce Import',
            'Shipping Address1': shipping_address.get('address_1', ''),
            'Shipping Address2': shipping_address.get('address_2', ''),
            'Shipping City': shipping_address.get('city', ''),
            'Shipping Province': shipping_address.get('state', ''),
            'Shipping Country': shipping_address.get('country', ''),
            'Shipping Zip': shipping_address.get('postcode', ''),
            'Shipping Phone': self.clean_phone(shipping_address.get('phone', '')),
            'Total Spent': customer.get('Total Spent', 0),
            'Total Orders': customer.get('Order Count', 0),
            'Notes': customer.get('Customer Note', ''),
            'Tax Exempt': customer.get('Tax Exempt', False),
        }

    def load_mailchimp_info_folder(self, folder_path: str) -> None:
        """
        Load MailChimp data from an info folder export.
        
        Args:
            folder_path (str): Path to the MailChimp info folder
        """
        folder_path = Path(folder_path)
        
        try:
            # Check if it's a zip file
            if str(folder_path).endswith('.zip'):
                print("Processing ZIP archive...")
                with zipfile.ZipFile(folder_path, 'r') as zip_ref:
                    temp_dir = folder_path.parent / 'temp_mailchimp'
                    zip_ref.extractall(temp_dir)
                    folder_path = temp_dir
            
            print(f"Reading MailChimp data from: {folder_path}")
            
            # Load lists/subscribers
            lists_path = folder_path / 'lists'
            if lists_path.exists():
                for list_folder in lists_path.iterdir():
                    if list_folder.is_dir():
                        # Load subscribers
                        subscribers_file = list_folder / 'members' / 'members.csv'
                        if subscribers_file.exists():
                            df = pd.read_csv(subscribers_file)
                            self.mailchimp_data['subscribers'].extend(df.to_dict('records'))
                            
                        # Load merge fields
                        merge_fields_file = list_folder / 'merge-fields.csv'
                        if merge_fields_file.exists():
                            df = pd.read_csv(merge_fields_file)
                            self.mailchimp_data['merge_fields'][list_folder.name] = df.to_dict('records')
                            
                        # Load segments
                        segments_file = list_folder / 'segments.csv'
                        if segments_file.exists():
                            df = pd.read_csv(segments_file)
                            self.mailchimp_data['segments'][list_folder.name] = df.to_dict('records')

            print(f"Found {len(self.mailchimp_data['subscribers'])} subscribers")
            
        except Exception as e:
            print(f"Error loading MailChimp info folder: {str(e)}")
            raise
        finally:
            # Clean up temp directory if it was created
            if 'temp_dir' in locals() and temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)

    def parse_mailchimp_subscriber(self, subscriber: Dict) -> Dict:
        """Convert MailChimp subscriber data to Shopify format."""
        email = subscriber.get('Email Address', '').lower()
        
        # Skip if we already have this customer from WooCommerce
        if email in self.seen_emails:
            return None

        # Get merge fields mapping for this list
        list_id = subscriber.get('List ID', '')
        merge_fields_map = {}
        if list_id in self.mailchimp_data['merge_fields']:
            for field in self.mailchimp_data['merge_fields'][list_id]:
                merge_fields_map[field['Tag']] = field['Name']

        # Parse MERGE fields using the mapping
        merge_data = {}
        for key, value in subscriber.items():
            if key.startswith('MERGE'):
                field_name = merge_fields_map.get(key, key)
                merge_data[field_name] = value

        # Get segments/tags for this subscriber
        tags = ['MailChimp Import', 'Newsletter Subscriber']
        list_id = subscriber.get('List ID', '')
        if list_id in self.mailchimp_data['segments']:
            for segment in self.mailchimp_data['segments'][list_id]:
                if subscriber.get('Email Address') in str(segment.get('Members', '')):
                    tags.append(segment['Name'])

        return {
            'Email': email,
            'First Name': subscriber.get('First Name', merge_data.get('First Name', '')),
            'Last Name': subscriber.get('Last Name', merge_data.get('Last Name', '')),
            'Company': merge_data.get('Company', ''),
            'Phone': self.clean_phone(merge_data.get('Phone', '')),
            'Address1': merge_data.get('Address', ''),
            'City': merge_data.get('City', ''),
            'Province': merge_data.get('State', ''),
            'Country': merge_data.get('Country', ''),
            'Zip': merge_data.get('Zip', ''),
            'Accepts Marketing': True,
            'Tags': ', '.join(tags),
            'Customer Type': 'newsletter_subscriber',
            'Marketing Source': 'MailChimp',
            'Subscription Status': subscriber.get('Status', ''),
            'List Name': subscriber.get('List Name', ''),
            'Signup Source': subscriber.get('Source', ''),
            'Last Modified': subscriber.get('Last Modified', ''),
            'Signup Location': subscriber.get('IP Signup', ''),
        }

    def convert_customers(self, woo_file: Optional[str] = None, 
                         mailchimp_folder: Optional[str] = None, 
                         output_file: str = 'shopify_customers.csv'):
        """
        Convert customers from WooCommerce and/or MailChimp to Shopify format.
        
        Args:
            woo_file (str, optional): Path to WooCommerce customers export CSV
            mailchimp_folder (str, optional): Path to MailChimp info folder
            output_file (str): Path to save Shopify-compatible CSV file
        """
        try:
            # Process WooCommerce customers first
            if woo_file:
                woo_df = pd.read_csv(woo_file)
                print(f"Processing {len(woo_df)} WooCommerce customers...")
                
                for _, customer in woo_df.iterrows():
                    customer_data = self.parse_woo_customer(customer)
                    self.seen_emails.add(customer_data['Email'])
                    self.shopify_customers.append(customer_data)

            # Process MailChimp subscribers
            if mailchimp_folder:
                self.load_mailchimp_info_folder(mailchimp_folder)
                print(f"Processing MailChimp subscribers...")
                
                for subscriber in self.mailchimp_data['subscribers']:
                    customer_data = self.parse_mailchimp_subscriber(subscriber)
                    if customer_data:  # Only add if not already exists
                        self.seen_emails.add(customer_data['Email'])
                        self.shopify_customers.append(customer_data)

            # Convert to DataFrame and save
            if self.shopify_customers:
                shopify_df = pd.DataFrame(self.shopify_customers)
                shopify_df.to_csv(output_file, index=False)
                
                print(f"\nConversion Summary:")
                print(f"Total unique customers: {len(self.shopify_customers)}")
                print(f"WooCommerce customers: {len([c for c in self.shopify_customers if 'Woocommerce Import' in c['Tags']])}")
                print(f"MailChimp subscribers: {len([c for c in self.shopify_customers if 'MailChimp Import' in c['Tags']])}")
                print(f"Output saved to: {output_file}")
            else:
                print("No customers found to convert!")

        except Exception as e:
            print(f"Error converting customers: {str(e)}")
            raise

def main():
    """Example usage of the CustomerMigrationTool."""
    tool = CustomerMigrationTool()
    
    # Example file paths
    woo_file = "woocommerce_customers_export.csv"
    mailchimp_folder = "info"  # Can be folder or zip file
    output_file = "shopify_customers_import.csv"
    
    # Convert customers
    tool.convert_customers(
        woo_file=woo_file,
        mailchimp_folder=mailchimp_folder,
        output_file=output_file
    )

if __name__ == "__main__":
    main()