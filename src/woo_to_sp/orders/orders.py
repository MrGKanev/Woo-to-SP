"""Order migration module for converting WooCommerce orders to Shopify format."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.config import OrderConfig


class OrderMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce orders to Shopify format."""

    TOOL_NAME = "order"
    REQUIRED_COLUMNS = ["order_number", "customer_email"]

    def __init__(self, config: Optional[OrderConfig] = None):
        super().__init__(config)
        self.meta_mapping: Dict[str, Dict[str, str]] = {}

    def _get_default_config(self) -> OrderConfig:
        return OrderConfig()

    def _init_stats(self) -> Dict[str, Any]:
        stats = super()._init_stats()
        stats.update({
            "line_items_created": 0,
            "meta_items_created": 0,
        })
        return stats

    def validate_item(self, order: Any) -> Tuple[bool, List[str]]:
        errors = []

        if not order.get("order_number"):
            errors.append("Missing order number")

        if not order.get("customer_email"):
            errors.append("Missing customer email")

        return len(errors) == 0, errors

    def load_meta_mapping(self, mapping_file: str) -> Dict[str, Dict[str, str]]:
        """Load meta mapping configuration from CSV file."""
        try:
            if Path(mapping_file).exists():
                df = pd.read_csv(mapping_file, encoding=self.config.encoding)
                mapping = {}
                for _, row in df.iterrows():
                    mapping[row["meta_key"]] = {
                        "name_prefix": row["name_prefix"]
                        if not pd.isna(row.get("name_prefix"))
                        else "",
                        "name_suffix": row["name_suffix"]
                        if not pd.isna(row.get("name_suffix"))
                        else "",
                        "sku_prefix": row["sku_prefix"]
                        if not pd.isna(row.get("sku_prefix"))
                        else "",
                        "price_field": row["price_field"]
                        if not pd.isna(row.get("price_field"))
                        else "",
                    }
                self.logger.info(f"Loaded {len(mapping)} meta mappings")
                return mapping
            else:
                self.logger.warning(f"Meta mapping file {mapping_file} not found")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading meta mapping: {e}")
            return {}

    def format_meta_name(self, key: str, value: str) -> str:
        """Format meta item name based on mapping configuration."""
        if key in self.meta_mapping:
            prefix = self.meta_mapping[key]["name_prefix"]
            suffix = self.meta_mapping[key]["name_suffix"]

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
        """Parse meta information from WooCommerce order item."""
        meta_items = []

        if not meta_str or pd.isna(meta_str):
            return meta_items

        meta_pairs = re.findall(r"meta:([^:]+):([^|]+)", str(meta_str))

        meta_values = {}
        for key, value in meta_pairs:
            meta_values[key] = value.strip()

        prices: Dict[str, float] = {}
        pao_match = re.search(r"meta:_pao_ids:([^|]+)", str(meta_str))
        if pao_match:
            pao_data = pao_match.group(1)
            price_matches = re.finditer(
                r's:3:"key";s:\d+:"([^"]+)";s:5:"value";s:\d+:"([^"]+)";.*?s:9:"raw_price";d:(\d+)',
                pao_data,
            )
            for match in price_matches:
                key, value, price = match.groups()
                try:
                    prices[key] = float(price)
                except ValueError:
                    pass

        for key, value in meta_values.items():
            if key in self.meta_mapping:
                if key.startswith("pa_"):
                    continue

                item_name = self.format_meta_name(key, value)
                sku_prefix = self.meta_mapping[key]["sku_prefix"]
                sku = f"{sku_prefix}{value.lower().replace(' ', '-')}"

                item_data = {
                    "name": item_name,
                    "quantity": 1,
                    "price": prices.get(key, 0),
                    "sku": sku,
                    "requires_shipping": True,
                    "taxable": True,
                }

                meta_items.append(item_data)
                self.stats["meta_items_created"] += 1

        return meta_items

    def convert_item(self, order: Any) -> Optional[List[Dict[str, Any]]]:
        """Convert a WooCommerce order to Shopify format. Returns multiple rows (one per line item)."""
        order_data = {
            "Name": f'#{order["order_number"]}',
            "Email": order["customer_email"],
            "Financial Status": "paid"
            if order.get("status") == "completed"
            else "pending",
            "Fulfillment Status": "fulfilled"
            if order.get("status") == "completed"
            else "unfulfilled",
            "Currency": order.get("order_currency", self.config.default_currency),
            "Created at": self.format_date(str(order.get("order_date", ""))),
            "Billing Name": f"{order.get('billing_first_name', '')} {order.get('billing_last_name', '')}".strip(),
            "Billing Street": order.get("billing_address_1", ""),
            "Billing Address2": order.get("billing_address_2", ""),
            "Billing Company": order.get("billing_company", ""),
            "Billing City": order.get("billing_city", ""),
            "Billing Province": order.get("billing_state", ""),
            "Billing Province Code": order.get("billing_state", ""),
            "Billing Zip": order.get("billing_postcode", ""),
            "Billing Country": order.get("billing_country", ""),
            "Billing Phone": self.clean_phone(order.get("billing_phone", "")),
            "Shipping Name": f"{order.get('shipping_first_name', '')} {order.get('shipping_last_name', '')}".strip(),
            "Shipping Street": order.get("shipping_address_1", ""),
            "Shipping Address2": order.get("shipping_address_2", ""),
            "Shipping Company": order.get("shipping_company", ""),
            "Shipping City": order.get("shipping_city", ""),
            "Shipping Province": order.get("shipping_state", ""),
            "Shipping Province Code": order.get("shipping_state", ""),
            "Shipping Zip": order.get("shipping_postcode", ""),
            "Shipping Country": order.get("shipping_country", ""),
            "Shipping Phone": self.clean_phone(order.get("shipping_phone", "")),
        }

        order_items: List[Dict[str, Any]] = []
        max_items = self.config.max_line_items

        for i in range(1, max_items + 1):
            line_item_key = f"line_item_{i}"
            if line_item_key not in order or pd.isna(order.get(line_item_key)):
                continue

            line_item = str(order[line_item_key])

            name_match = re.search(r"name:([^|]+)", line_item)
            qty_match = re.search(r"quantity:(\d+)", line_item)
            total_match = re.search(r"total:(\d+\.?\d*)", line_item)
            sku_match = re.search(r"sku:([^|]+)", line_item)

            if name_match and qty_match and total_match:
                try:
                    quantity = int(qty_match.group(1))
                    total = float(total_match.group(1))
                except (ValueError, TypeError):
                    self.logger.warning(
                        f"Skipping malformed line item {i} in order {order.get('order_number')}"
                    )
                    continue

                main_item = {
                    "name": name_match.group(1).strip(),
                    "quantity": quantity,
                    "price": total / quantity if quantity > 0 else 0,
                    "sku": sku_match.group(1).strip() if sku_match else "",
                    "requires_shipping": True,
                    "taxable": True,
                }
                order_items.append(main_item)
                self.stats["line_items_created"] += 1

                meta_items = self.parse_meta_info(line_item)
                order_items.extend(meta_items)

        shopify_orders = []
        for idx, item in enumerate(order_items):
            item_order = order_data.copy()
            item_order.update({
                "Lineitem name": item["name"],
                "Lineitem quantity": item["quantity"],
                "Lineitem price": item["price"],
                "Lineitem sku": item["sku"],
                "Lineitem requires shipping": "true"
                if item["requires_shipping"]
                else "false",
                "Lineitem taxable": "true" if item["taxable"] else "false",
            })

            if idx == 0:
                item_order.update({
                    "Taxes Included": "false",
                    "Tax 1 Name": "Tax",
                    "Tax 1 Value": order.get("tax_total", 0),
                    "Shipping Line Title": order.get(
                        "shipping_method", "Standard"
                    ),
                    "Shipping Line Price": order.get("shipping_total", 0),
                    "Total": order.get("order_total", 0),
                })

            shopify_orders.append(item_order)

        return shopify_orders if shopify_orders else None

    def convert_orders(
        self,
        input_file: str,
        output_file: str,
        meta_mapping_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        """Convert WooCommerce orders to Shopify format."""
        if meta_mapping_file:
            self.meta_mapping = self.load_meta_mapping(meta_mapping_file)

        self.convert_data(input_file, output_file, dry_run=dry_run)
