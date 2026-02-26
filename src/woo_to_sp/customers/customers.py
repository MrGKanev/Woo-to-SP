"""Customer migration module for converting WooCommerce customers and MailChimp subscribers to Shopify format."""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.config import CustomerConfig


class CustomerMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce customers and MailChimp subscribers to Shopify."""

    TOOL_NAME = "customer"

    def __init__(self, config: Optional[CustomerConfig] = None):
        super().__init__(config)
        self.seen_emails: set = set()
        self.mailchimp_data: Dict[str, Any] = {
            "subscribers": [],
            "merge_fields": {},
            "segments": {},
        }

    def _get_default_config(self) -> CustomerConfig:
        return CustomerConfig()

    def _init_stats(self) -> Dict[str, Any]:
        stats = super()._init_stats()
        stats.update({
            "woocommerce_customers": 0,
            "mailchimp_subscribers": 0,
            "duplicates_skipped": 0,
        })
        return stats

    def validate_item(self, customer: Any) -> Tuple[bool, List[str]]:
        errors = []

        email = str(customer.get("Email", "")).lower().strip()
        if not email:
            errors.append("Missing email address")

        if email in self.seen_emails:
            self.stats["duplicates_skipped"] += 1
            errors.append("Duplicate email")

        return len(errors) == 0, errors

    def parse_address(self, address_str: Any) -> Dict[str, Any]:
        """Parse address string into components."""
        if pd.isna(address_str) or address_str is None:
            return {}

        if isinstance(address_str, dict):
            return address_str

        if isinstance(address_str, str):
            text = address_str.strip()
            if text.startswith("{") or text.startswith("["):
                try:
                    result = json.loads(text)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    pass
        return {}

    def convert_item(self, customer: Any) -> Optional[Dict[str, Any]]:
        billing_address = self.parse_address(customer.get("Billing Address", {}))
        shipping_address = self.parse_address(customer.get("Shipping Address", {}))

        email = str(customer.get("Email", "")).lower().strip()
        self.seen_emails.add(email)
        self.stats["woocommerce_customers"] += 1

        return {
            "Email": email,
            "First Name": customer.get(
                "First Name", billing_address.get("first_name", "")
            ),
            "Last Name": customer.get(
                "Last Name", billing_address.get("last_name", "")
            ),
            "Company": billing_address.get("company", ""),
            "Phone": self.clean_phone(billing_address.get("phone", "")),
            "Address1": billing_address.get("address_1", ""),
            "Address2": billing_address.get("address_2", ""),
            "City": billing_address.get("city", ""),
            "Province": billing_address.get("state", ""),
            "Province Code": billing_address.get("state", ""),
            "Country": billing_address.get("country", ""),
            "Zip": billing_address.get("postcode", ""),
            "Customer Type": "regular",
            "Accepts Marketing": str(
                customer.get("Accepts Marketing", "no")
            ).lower()
            in ["yes", "true", "1"],
            "Tags": "Woocommerce Import",
            "Shipping Address1": shipping_address.get("address_1", ""),
            "Shipping Address2": shipping_address.get("address_2", ""),
            "Shipping City": shipping_address.get("city", ""),
            "Shipping Province": shipping_address.get("state", ""),
            "Shipping Country": shipping_address.get("country", ""),
            "Shipping Zip": shipping_address.get("postcode", ""),
            "Shipping Phone": self.clean_phone(shipping_address.get("phone", "")),
            "Total Spent": customer.get("Total Spent", 0),
            "Total Orders": customer.get("Order Count", 0),
            "Notes": self.clean_text(customer.get("Customer Note", "")),
            "Tax Exempt": customer.get("Tax Exempt", False),
        }

    def load_mailchimp_info_folder(self, folder_path: str) -> None:
        """Load MailChimp data from an info folder export."""
        folder = Path(folder_path)
        temp_dir: Optional[Path] = None

        try:
            if str(folder).endswith(".zip"):
                self.logger.info("Processing ZIP archive...")
                temp_dir = folder.parent / "temp_mailchimp"
                with zipfile.ZipFile(folder, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                folder = temp_dir

            self.logger.info(f"Reading MailChimp data from: {folder}")

            lists_path = folder / "lists"
            if lists_path.exists():
                for list_folder in lists_path.iterdir():
                    if list_folder.is_dir():
                        subscribers_file = list_folder / "members" / "members.csv"
                        if subscribers_file.exists():
                            df = pd.read_csv(
                                subscribers_file, encoding=self.config.encoding
                            )
                            self.mailchimp_data["subscribers"].extend(
                                df.to_dict("records")
                            )

                        merge_fields_file = list_folder / "merge-fields.csv"
                        if merge_fields_file.exists():
                            df = pd.read_csv(
                                merge_fields_file, encoding=self.config.encoding
                            )
                            self.mailchimp_data["merge_fields"][list_folder.name] = (
                                df.to_dict("records")
                            )

                        segments_file = list_folder / "segments.csv"
                        if segments_file.exists():
                            df = pd.read_csv(
                                segments_file, encoding=self.config.encoding
                            )
                            self.mailchimp_data["segments"][list_folder.name] = (
                                df.to_dict("records")
                            )

            self.logger.info(
                f"Found {len(self.mailchimp_data['subscribers'])} MailChimp subscribers"
            )

        except Exception as e:
            self.logger.error(f"Error loading MailChimp info folder: {e}")
            raise
        finally:
            if temp_dir is not None and temp_dir.exists():
                shutil.rmtree(temp_dir)

    def convert_mailchimp_subscriber(
        self, subscriber: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert MailChimp subscriber data to Shopify format."""
        email = str(subscriber.get("Email Address", "")).lower().strip()

        if email in self.seen_emails:
            self.stats["duplicates_skipped"] += 1
            return None

        list_id = subscriber.get("List ID", "")
        merge_fields_map: Dict[str, str] = {}
        if list_id in self.mailchimp_data["merge_fields"]:
            for field in self.mailchimp_data["merge_fields"][list_id]:
                merge_fields_map[field["Tag"]] = field["Name"]

        merge_data: Dict[str, Any] = {}
        for key, value in subscriber.items():
            if key.startswith("MERGE"):
                field_name = merge_fields_map.get(key, key)
                merge_data[field_name] = value

        tags = ["MailChimp Import", "Newsletter Subscriber"]
        if list_id in self.mailchimp_data["segments"]:
            for segment in self.mailchimp_data["segments"][list_id]:
                if subscriber.get("Email Address") in str(
                    segment.get("Members", "")
                ):
                    tags.append(segment["Name"])

        self.seen_emails.add(email)
        self.stats["mailchimp_subscribers"] += 1

        return {
            "Email": email,
            "First Name": subscriber.get(
                "First Name", merge_data.get("First Name", "")
            ),
            "Last Name": subscriber.get(
                "Last Name", merge_data.get("Last Name", "")
            ),
            "Company": merge_data.get("Company", ""),
            "Phone": self.clean_phone(merge_data.get("Phone", "")),
            "Address1": merge_data.get("Address", ""),
            "City": merge_data.get("City", ""),
            "Province": merge_data.get("State", ""),
            "Country": merge_data.get("Country", ""),
            "Zip": merge_data.get("Zip", ""),
            "Accepts Marketing": True,
            "Tags": ", ".join(tags),
            "Customer Type": "newsletter_subscriber",
            "Marketing Source": "MailChimp",
            "Subscription Status": subscriber.get("Status", ""),
            "List Name": subscriber.get("List Name", ""),
            "Signup Source": subscriber.get("Source", ""),
        }

    def convert_customers(
        self,
        woo_file: Optional[str] = None,
        mailchimp_folder: Optional[str] = None,
        output_file: str = "shopify_customers.csv",
        dry_run: bool = False,
    ) -> None:
        """Convert customers from WooCommerce and/or MailChimp to Shopify format."""
        self.stats["start_time"] = datetime.now()

        converted_customers: List[Dict[str, Any]] = []

        try:
            if woo_file and Path(woo_file).exists():
                self.logger.info(f"Processing WooCommerce customers from {woo_file}")
                woo_df = pd.read_csv(woo_file, encoding=self.config.encoding)

                if self.config.show_progress:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        MofNCompleteColumn(),
                    ) as progress:
                        task = progress.add_task(
                            "WooCommerce customers", total=len(woo_df)
                        )
                        for _, customer in woo_df.iterrows():
                            self._process_woo_customer(customer, converted_customers)
                            progress.advance(task)
                else:
                    for _, customer in woo_df.iterrows():
                        self._process_woo_customer(customer, converted_customers)

            if mailchimp_folder and Path(mailchimp_folder).exists():
                self.load_mailchimp_info_folder(mailchimp_folder)
                self.logger.info("Processing MailChimp subscribers...")

                subscribers = self.mailchimp_data["subscribers"]
                if self.config.show_progress:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        MofNCompleteColumn(),
                    ) as progress:
                        task = progress.add_task(
                            "MailChimp subscribers", total=len(subscribers)
                        )
                        for subscriber in subscribers:
                            self._process_mc_subscriber(
                                subscriber, converted_customers
                            )
                            progress.advance(task)
                else:
                    for subscriber in subscribers:
                        self._process_mc_subscriber(subscriber, converted_customers)

            self.stats["total_items"] = (
                self.stats["woocommerce_customers"]
                + self.stats["mailchimp_subscribers"]
                + self.stats["duplicates_skipped"]
            )

            if dry_run:
                self.logger.info(
                    f"Dry run: {len(converted_customers)} customers would be written"
                )
            elif converted_customers:
                shopify_df = pd.DataFrame(converted_customers)
                shopify_df.to_csv(
                    output_file, index=False, encoding=self.config.encoding
                )
                self.logger.info(
                    f"Saved {len(converted_customers)} customers to {output_file}"
                )
            else:
                self.logger.warning("No customers found to convert!")

            self.stats["end_time"] = datetime.now()
            self.generate_report(output_file)

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            raise

    def _process_woo_customer(
        self, customer: Any, results: List[Dict[str, Any]]
    ) -> None:
        try:
            is_valid, errors = self.validate_item(customer)
            if is_valid:
                converted = self.convert_item(customer)
                if converted:
                    results.append(converted)
                    self.stats["successful"] += 1
            else:
                if "Duplicate email" not in errors:
                    self.stats["warnings"] += 1
        except Exception as e:
            self.logger.error(f"Error processing WooCommerce customer: {e}")
            self.stats["failed"] += 1

    def _process_mc_subscriber(
        self, subscriber: Dict[str, Any], results: List[Dict[str, Any]]
    ) -> None:
        try:
            converted = self.convert_mailchimp_subscriber(subscriber)
            if converted:
                results.append(converted)
                self.stats["successful"] += 1
        except Exception as e:
            self.logger.error(f"Error processing MailChimp subscriber: {e}")
            self.stats["failed"] += 1
