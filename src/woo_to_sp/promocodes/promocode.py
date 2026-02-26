"""Discount codes migration module for converting WooCommerce coupons to Shopify discount codes."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.config import DiscountConfig


class DiscountMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce coupons to Shopify discount codes."""

    TOOL_NAME = "discount"
    REQUIRED_COLUMNS = ["code"]

    def __init__(self, config: Optional[DiscountConfig] = None):
        super().__init__(config)
        self.product_mapping: Dict[str, str] = {}

    def _get_default_config(self) -> DiscountConfig:
        return DiscountConfig()

    def _init_stats(self) -> Dict[str, Any]:
        stats = super()._init_stats()
        stats.update({
            "percentage_discounts": 0,
            "fixed_discounts": 0,
            "codes_truncated": 0,
        })
        return stats

    def validate_item(self, coupon: Any) -> Tuple[bool, List[str]]:
        errors = []

        if not coupon.get("code"):
            errors.append("Missing discount code")

        try:
            amount = float(coupon.get("amount", 0))
            if amount < 0:
                errors.append("Discount amount cannot be negative")
        except (ValueError, TypeError):
            errors.append("Invalid discount amount")

        return len(errors) == 0, errors

    def clean_discount_code(self, code: str) -> str:
        """Clean and validate discount code."""
        if not code:
            return ""

        code = re.sub(r"[^A-Z0-9_-]", "", str(code).upper())

        max_length = self.config.max_code_length
        if len(code) > max_length:
            code = code[:max_length]
            self.stats["codes_truncated"] += 1

        return code

    def convert_amount_type(
        self, woo_type: str, amount: float
    ) -> Tuple[str, float]:
        """Convert WooCommerce discount type to Shopify format."""
        if woo_type == "percent":
            self.stats["percentage_discounts"] += 1
            return "percentage", amount
        elif woo_type in ["fixed_cart", "fixed_product"]:
            self.stats["fixed_discounts"] += 1
            return "fixed_amount", amount
        else:
            self.stats["percentage_discounts"] += 1
            return "percentage", amount

    def process_product_restrictions(
        self,
        included_products: str,
        excluded_products: str,
    ) -> Dict[str, List[str]]:
        """Process product restrictions for Shopify format."""
        restrictions: Dict[str, List[str]] = {
            "entitled_product_ids": [],
            "excluded_product_ids": [],
        }

        if included_products and not pd.isna(included_products):
            restrictions["entitled_product_ids"] = [
                str(pid).strip()
                for pid in str(included_products).split(",")
                if pid.strip()
            ]

        if excluded_products and not pd.isna(excluded_products):
            restrictions["excluded_product_ids"] = [
                str(pid).strip()
                for pid in str(excluded_products).split(",")
                if pid.strip()
            ]

        return restrictions

    def convert_item(self, coupon: Any) -> Optional[Dict[str, Any]]:
        code = self.clean_discount_code(coupon["code"])
        if not code:
            self.logger.warning(
                f"Invalid coupon code after cleaning: {coupon['code']}"
            )
            return None

        discount_type, amount = self.convert_amount_type(
            coupon.get("discount_type", "percent"),
            float(coupon.get("amount", 0) or 0),
        )

        restrictions = self.process_product_restrictions(
            coupon.get("product_ids", ""),
            coupon.get("exclude_product_ids", ""),
        )

        return {
            "Discount Code": code,
            "Type": discount_type,
            "Amount": amount,
            "Minimum Purchase Amount": coupon.get(
                "minimum_amount", self.config.default_minimum_amount
            ),
            "Starts At": self.format_date(str(coupon.get("date_created", ""))),
            "Ends At": self.format_date(str(coupon.get("date_expires", ""))),
            "Usage Limit": coupon.get("usage_limit", self.config.default_usage_limit),
            "Once Per Customer": str(coupon.get("individual_use", "no")).lower()
            == "yes",
            "Status": "enabled"
            if str(coupon.get("enabled", "yes")).lower() == "yes"
            else "disabled",
            "Applies To": "all"
            if not restrictions["entitled_product_ids"]
            else "specific",
            "Products": ",".join(restrictions["entitled_product_ids"]),
            "Excluded Products": ",".join(restrictions["excluded_product_ids"]),
            "Description": self.clean_text(coupon.get("description", "")),
            "Times Used": int(coupon.get("usage_count", 0) or 0),
        }

    def convert_discounts(
        self,
        input_file: str,
        output_file: str,
        product_mapping_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        """Convert WooCommerce coupons to Shopify discount codes."""
        if product_mapping_file and Path(product_mapping_file).exists():
            mapping_df = pd.read_csv(
                product_mapping_file, encoding=self.config.encoding
            )
            self.product_mapping = self.load_mapping(mapping_df)
            self.logger.info(f"Loaded {len(self.product_mapping)} product mappings")

        self.convert_data(input_file, output_file, dry_run=dry_run)

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """Load product ID mapping."""
        if "woo_id" in mapping_df.columns and "shopify_id" in mapping_df.columns:
            return dict(
                zip(
                    mapping_df["woo_id"].astype(str),
                    mapping_df["shopify_id"].astype(str),
                )
            )
        return {}
