# customers/customers.py
"""Customer migration module for converting WooCommerce customers and MailChimp subscribers to Shopify format."""

import pandas as pd
import json
from datetime import datetime
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import zipfile
import shutil
import logging
import argparse


class CustomerMigrationTool:
    """Tool for migrating WooCommerce customers and MailChimp subscribers to Shopify."""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize migration tool with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.setup_logging()
        self.shopify_customers: List[Dict[str, Any]] = []
        self.seen_emails: set = set()
        self.mailchimp_data: Dict[str, Any] = {
            'subscribers': [],
            'merge_fields': {},
            'segments': {},
            'activities': {}
        }
        self.stats = {
            'total_customers': 0,
            'woocommerce_customers': 0,
            'mailchimp_subscribers': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'duplicates_skipped': 0
        }

    def setup_logging(self) -> None:
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f'customer_migration_{datetime.now():%Y%m%d_%H%M%S}.log'

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def clean_phone(self, phone: Optional[str]) -> str:
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

    def parse_address(self, address_str: Any) -> Dict[str, Any]:
        """
        Parse address string into components.

        Args:
            address_str: Address data (string, dict, or JSON string)

        Returns:
            Dictionary with address components
        """
        try:
            if isinstance(address_str, str) and (address_str.startswith('{') or address_str.startswith('[')):
                return json.loads(address_str)
            return address_str if isinstance(address_str, dict) else {}
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            self.logger.debug(f"Could not parse address: {e}")
            return {}

    def parse_woo_customer(self, customer: pd.Series) -> Dict[str, Any]:
        """
        Convert WooCommerce customer data to Shopify format.

        Args:
            customer: WooCommerce customer row

        Returns:
            Dictionary with Shopify customer format
        """
        billing_address = self.parse_address(customer.get('Billing Address', {}))
        shipping_address = self.parse_address(customer.get('Shipping Address', {}))

        return {
            'Email': str(customer.get('Email', '')).lower(),
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
            'Notes': customer.get('Customer Note', ''),
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

            self.logger.info(f"Found {len(self.mailchimp_data['subscribers'])} subscribers")

        except Exception as e:
            self.logger.error(f"Error loading MailChimp info folder: {str(e)}")
            raise
        finally:
            # Clean up temp directory if it was created
            if temp_dir is not None and temp_dir.exists():
                shutil.rmtree(temp_dir)

    def parse_mailchimp_subscriber(self, subscriber: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert MailChimp subscriber data to Shopify format.

        Args:
            subscriber: MailChimp subscriber data

        Returns:
            Dictionary with Shopify customer format, or None if duplicate
        """
        email = str(subscriber.get('Email Address', '')).lower()

        # Skip if we already have this customer from WooCommerce
        if email in self.seen_emails:
            self.stats['duplicates_skipped'] += 1
            return None

        # Get merge fields mapping for this list
        list_id = subscriber.get('List ID', '')
        merge_fields_map: Dict[str, str] = {}
        if list_id in self.mailchimp_data['merge_fields']:
            for field in self.mailchimp_data['merge_fields'][list_id]:
                merge_fields_map[field['Tag']] = field['Name']

        # Parse MERGE fields using the mapping
        merge_data: Dict[str, Any] = {}
        for key, value in subscriber.items():
            if key.startswith('MERGE'):
                field_name = merge_fields_map.get(key, key)
                merge_data[field_name] = value

        # Get segments/tags for this subscriber
        tags = ['MailChimp Import', 'Newsletter Subscriber']
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
        try:
            self.logger.info("Starting customer migration")

            # Process WooCommerce customers first
            if woo_file:
                woo_df = pd.read_csv(woo_file)
                self.logger.info(f"Processing {len(woo_df)} WooCommerce customers...")

                for _, customer in woo_df.iterrows():
                    try:
                        customer_data = self.parse_woo_customer(customer)
                        self.seen_emails.add(customer_data['Email'])
                        self.shopify_customers.append(customer_data)
                        self.stats['woocommerce_customers'] += 1
                        self.stats['successful'] += 1
                    except Exception as e:
                        self.logger.error(f"Error processing WooCommerce customer: {str(e)}")
                        self.stats['failed'] += 1

            # Process MailChimp subscribers
            if mailchimp_folder:
                self.load_mailchimp_info_folder(mailchimp_folder)
                self.logger.info("Processing MailChimp subscribers...")

                for subscriber in self.mailchimp_data['subscribers']:
                    try:
                        customer_data = self.parse_mailchimp_subscriber(subscriber)
                        if customer_data:  # Only add if not already exists
                            self.seen_emails.add(customer_data['Email'])
                            self.shopify_customers.append(customer_data)
                            self.stats['mailchimp_subscribers'] += 1
                            self.stats['successful'] += 1
                    except Exception as e:
                        self.logger.error(f"Error processing MailChimp subscriber: {str(e)}")
                        self.stats['failed'] += 1

            # Update total count
            self.stats['total_customers'] = len(self.shopify_customers)

            # Convert to DataFrame and save
            if self.shopify_customers:
                shopify_df = pd.DataFrame(self.shopify_customers)
                shopify_df.to_csv(output_file, index=False)

                # Generate report
                self.generate_report(output_file)

                self.logger.info("Conversion Summary:")
                self.logger.info(f"Total unique customers: {len(self.shopify_customers)}")
                self.logger.info(f"WooCommerce customers: {self.stats['woocommerce_customers']}")
                self.logger.info(f"MailChimp subscribers: {self.stats['mailchimp_subscribers']}")
                self.logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
                self.logger.info(f"Output saved to: {output_file}")
            else:
                self.logger.warning("No customers found to convert!")

        except Exception as e:
            self.logger.error(f"Error converting customers: {str(e)}")
            raise

    def generate_report(self, output_file: str) -> None:
        """
        Generate migration report.

        Args:
            output_file: Path to the output file
        """
        total = max(self.stats['total_customers'], 1)
        report = {
            'timestamp': datetime.now().isoformat(),
            'output_file': output_file,
            'statistics': self.stats,
            'success_rate': f"{(self.stats['successful'] / total * 100):.2f}%",
            'configuration': self.config
        }

        # Save report
        report_file = Path('reports') / f'customer_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Migration report saved to {report_file}")


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

    args = parser.parse_args()

    if not args.woo_file and not args.mailchimp_folder:
        parser.error("At least one of --woo-file or --mailchimp-folder is required")

    tool = CustomerMigrationTool()

    try:
        tool.convert_customers(
            woo_file=args.woo_file,
            mailchimp_folder=args.mailchimp_folder,
            output_file=args.output
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
