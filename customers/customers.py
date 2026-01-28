# customers/customers.py
"""Customer migration module for converting WooCommerce customers and MailChimp subscribers to Shopify format."""

import pandas as pd
import json
from pathlib import Path
import zipfile
import shutil
from typing import Dict, List, Optional, Tuple, Any
import argparse
import sys
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from base.base_migration import BaseMigrationTool


class CustomerMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce customers and MailChimp subscribers to Shopify."""

    TOOL_NAME = "customer"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize customer migration tool."""
        super().__init__(config)
        self.seen_emails: set = set()
        self.mailchimp_data: Dict[str, Any] = {
            'subscribers': [],
            'merge_fields': {},
            'segments': {},
        }

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics for customer migration."""
        stats = super()._init_stats()
        stats.update({
            'woocommerce_customers': 0,
            'mailchimp_subscribers': 0,
            'duplicates_skipped': 0,
        })
        return stats

    def validate_item(self, customer: Any) -> Tuple[bool, List[str]]:
        """
        Validate customer data before conversion.

        Args:
            customer: Customer data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        email = str(customer.get('Email', '')).lower().strip()
        if not email:
            errors.append("Missing email address")

        # Check for duplicates
        if email in self.seen_emails:
            self.stats['duplicates_skipped'] += 1
            errors.append("Duplicate email")

        return len(errors) == 0, errors

    def parse_address(self, address_str: Any) -> Dict[str, Any]:
        """
        Parse address string into components.

        Args:
            address_str: Address data (string, dict, or JSON string)

        Returns:
            Dictionary with address components
        """
        if pd.isna(address_str) or address_str is None:
            return {}

        if isinstance(address_str, dict):
            return address_str

        if isinstance(address_str, str):
            if address_str.startswith('{') or address_str.startswith('['):
                try:
                    return json.loads(address_str)
                except json.JSONDecodeError:
                    pass
        return {}

    def convert_item(self, customer: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a WooCommerce customer to Shopify format.

        Args:
            customer: Customer data to convert

        Returns:
            Converted customer data for Shopify
        """
        billing_address = self.parse_address(customer.get('Billing Address', {}))
        shipping_address = self.parse_address(customer.get('Shipping Address', {}))

        email = str(customer.get('Email', '')).lower().strip()
        self.seen_emails.add(email)
        self.stats['woocommerce_customers'] += 1

        return {
            'Email': email,
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
            'Accepts Marketing': str(customer.get('Accepts Marketing', 'no')).lower() in ['yes', 'true', '1'],
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
            'Notes': self.clean_text(customer.get('Customer Note', '')),
            'Tax Exempt': customer.get('Tax Exempt', False),
        }

    def load_mailchimp_info_folder(self, folder_path: str) -> None:
        """
        Load MailChimp data from an info folder export.

        Args:
            folder_path: Path to the MailChimp info folder or zip file
        """
        folder_path = Path(folder_path)
        temp_dir: Optional[Path] = None

        try:
            # Check if it's a zip file
            if str(folder_path).endswith('.zip'):
                self.logger.info("Processing ZIP archive...")
                temp_dir = folder_path.parent / 'temp_mailchimp'
                with zipfile.ZipFile(folder_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                folder_path = temp_dir

            self.logger.info(f"Reading MailChimp data from: {folder_path}")

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

            self.logger.info(f"Found {len(self.mailchimp_data['subscribers'])} MailChimp subscribers")

        except Exception as e:
            self.logger.error(f"Error loading MailChimp info folder: {str(e)}")
            raise
        finally:
            if temp_dir is not None and temp_dir.exists():
                shutil.rmtree(temp_dir)

    def convert_mailchimp_subscriber(self, subscriber: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert MailChimp subscriber data to Shopify format.

        Args:
            subscriber: MailChimp subscriber data

        Returns:
            Converted customer data, or None if duplicate
        """
        email = str(subscriber.get('Email Address', '')).lower().strip()

        if email in self.seen_emails:
            self.stats['duplicates_skipped'] += 1
            return None

        # Get merge fields mapping
        list_id = subscriber.get('List ID', '')
        merge_fields_map: Dict[str, str] = {}
        if list_id in self.mailchimp_data['merge_fields']:
            for field in self.mailchimp_data['merge_fields'][list_id]:
                merge_fields_map[field['Tag']] = field['Name']

        # Parse MERGE fields
        merge_data: Dict[str, Any] = {}
        for key, value in subscriber.items():
            if key.startswith('MERGE'):
                field_name = merge_fields_map.get(key, key)
                merge_data[field_name] = value

        # Get tags
        tags = ['MailChimp Import', 'Newsletter Subscriber']
        if list_id in self.mailchimp_data['segments']:
            for segment in self.mailchimp_data['segments'][list_id]:
                if subscriber.get('Email Address') in str(segment.get('Members', '')):
                    tags.append(segment['Name'])

        self.seen_emails.add(email)
        self.stats['mailchimp_subscribers'] += 1

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
        }

    def convert_customers(
        self,
        woo_file: Optional[str] = None,
        mailchimp_folder: Optional[str] = None,
        output_file: str = 'shopify_customers.csv'
    ) -> None:
        """
        Convert customers from WooCommerce and/or MailChimp to Shopify format.

        Args:
            woo_file: Path to WooCommerce customers export CSV
            mailchimp_folder: Path to MailChimp info folder
            output_file: Path to save Shopify-compatible CSV file
        """
        from datetime import datetime
        self.stats['start_time'] = datetime.now()

        converted_customers: List[Dict[str, Any]] = []

        try:
            # Process WooCommerce customers first
            if woo_file and Path(woo_file).exists():
                self.logger.info(f"Processing WooCommerce customers from {woo_file}")
                woo_df = pd.read_csv(woo_file)

                iterator = woo_df.iterrows()
                if self.config.get('show_progress', True):
                    iterator = tqdm(iterator, total=len(woo_df), desc="WooCommerce customers")

                for _, customer in iterator:
                    is_valid, errors = self.validate_item(customer)
                    if is_valid:
                        converted = self.convert_item(customer)
                        if converted:
                            converted_customers.append(converted)
                            self.stats['successful'] += 1
                    else:
                        if 'Duplicate email' not in errors:
                            self.stats['warnings'] += 1

            # Process MailChimp subscribers
            if mailchimp_folder and Path(mailchimp_folder).exists():
                self.load_mailchimp_info_folder(mailchimp_folder)
                self.logger.info("Processing MailChimp subscribers...")

                iterator = self.mailchimp_data['subscribers']
                if self.config.get('show_progress', True):
                    iterator = tqdm(iterator, desc="MailChimp subscribers")

                for subscriber in iterator:
                    try:
                        converted = self.convert_mailchimp_subscriber(subscriber)
                        if converted:
                            converted_customers.append(converted)
                            self.stats['successful'] += 1
                    except Exception as e:
                        self.logger.error(f"Error processing MailChimp subscriber: {str(e)}")
                        self.stats['failed'] += 1

            # Update total count
            self.stats['total_items'] = len(converted_customers)

            # Save to CSV
            if converted_customers:
                shopify_df = pd.DataFrame(converted_customers)
                shopify_df.to_csv(output_file, index=False)
                self.logger.info(f"Saved {len(converted_customers)} customers to {output_file}")

                # Generate report
                self.stats['end_time'] = datetime.now()
                self.generate_report(output_file)
                self._log_summary()
            else:
                self.logger.warning("No customers found to convert!")

        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise


def main():
    """CLI entry point for customer migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce customers and MailChimp subscribers to Shopify format'
    )
    parser.add_argument(
        '-w', '--woo-file',
        default=None,
        help='Path to WooCommerce customers export CSV'
    )
    parser.add_argument(
        '-m', '--mailchimp-folder',
        default=None,
        help='Path to MailChimp info folder or zip file'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_customers_import.csv',
        help='Path to save Shopify customers CSV'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    if not args.woo_file and not args.mailchimp_folder:
        parser.error("At least one of --woo-file or --mailchimp-folder is required")

    config = {
        'show_progress': not args.no_progress,
    }

    tool = CustomerMigrationTool(config)

    try:
        tool.convert_customers(
            woo_file=args.woo_file,
            mailchimp_folder=args.mailchimp_folder,
            output_file=args.output
        )
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
