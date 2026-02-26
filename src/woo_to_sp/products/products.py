"""Product migration module for converting WooCommerce products to Shopify format."""

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import pandas as pd

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.config import ProductConfig


@dataclass
class ProductVariant:
    """Data class for product variants."""

    sku: str = ""
    price: float = 0.0
    compare_at_price: Optional[float] = None
    weight: float = 0.0
    weight_unit: str = "kg"
    inventory_quantity: int = 0
    option1: Optional[str] = None
    option2: Optional[str] = None
    option3: Optional[str] = None


class ProductMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce products to Shopify."""

    TOOL_NAME = "product"
    REQUIRED_COLUMNS = ["post_title"]

    def __init__(self, config: Optional[ProductConfig] = None):
        super().__init__(config)
        self.image_mapping: Dict[str, str] = {}

    def _get_default_config(self) -> ProductConfig:
        return ProductConfig()

    def _init_stats(self) -> Dict[str, Any]:
        stats = super()._init_stats()
        stats.update({
            "variants_processed": 0,
            "images_processed": 0,
            "drafts_skipped": 0,
        })
        return stats

    def validate_item(self, product: Any) -> Tuple[bool, List[str]]:
        errors = []

        if not product.get("post_title"):
            errors.append("Missing product title")

        if self.config.skip_drafts and product.get("status") == "draft":
            self.stats["drafts_skipped"] += 1
            errors.append("Draft product skipped")

        return len(errors) == 0, errors

    def process_images(
        self,
        image_urls: List[str],
        product_id: str,
    ) -> List[Dict[str, Any]]:
        """Process product images and prepare for Shopify import."""
        if not self.config.image_migration:
            return []

        processed_images = []

        for position, url in enumerate(image_urls, 1):
            try:
                url = str(url).strip()
                parsed_url = urlparse(url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    self.logger.warning(f"Invalid image URL for product {product_id}: {url}")
                    continue

                mapped_url = self.image_mapping.get(url, url)

                image_data = {
                    "src": mapped_url,
                    "position": position,
                    "alt": f"Product image {position}",
                }

                processed_images.append(image_data)
                self.stats["images_processed"] += 1

            except Exception as e:
                self.logger.error(
                    f"Error processing image {url} for product {product_id}: {e}"
                )

        return processed_images

    def process_variants(self, variants_data: List[Dict[str, Any]]) -> List[ProductVariant]:
        """Process product variants data."""
        processed_variants = []

        for variant_data in variants_data:
            try:
                compare_at = None
                if variant_data.get("regular_price"):
                    try:
                        regular = float(variant_data["regular_price"])
                        sale = float(variant_data.get("price", 0))
                        if regular > sale:
                            compare_at = regular
                    except (ValueError, TypeError):
                        pass

                variant = ProductVariant(
                    sku=str(variant_data.get("sku", "")),
                    price=float(variant_data.get("price", 0) or 0),
                    compare_at_price=compare_at,
                    weight=float(variant_data.get("weight", 0) or 0),
                    weight_unit=variant_data.get(
                        "weight_unit", self.config.default_weight_unit
                    ),
                    inventory_quantity=int(variant_data.get("stock_quantity", 0) or 0),
                    option1=variant_data.get("attribute_1"),
                    option2=variant_data.get("attribute_2"),
                    option3=variant_data.get("attribute_3"),
                )

                processed_variants.append(variant)
                self.stats["variants_processed"] += 1

            except Exception as e:
                self.logger.error(f"Error processing variant: {e}")

        return processed_variants

    def convert_item(self, product: Any) -> Optional[Dict[str, Any]]:
        product_id = product.get("ID", "unknown")

        shopify_product = {
            "Handle": self.create_handle(product["post_title"]),
            "Title": product["post_title"],
            "Body (HTML)": self.clean_html(str(product.get("post_content", ""))),
            "Vendor": self.clean_text(product.get("vendor", "")),
            "Type": self.clean_text(product.get("product_type", "")),
            "Tags": self.clean_text(product.get("tags", "")),
            "Published": product.get("status") == "publish",
            "Option1 Name": product.get("attribute_1_name"),
            "Option2 Name": product.get("attribute_2_name"),
            "Option3 Name": product.get("attribute_3_name"),
        }

        variants_json = product.get("variations", "[]")
        variants_data = self.parse_json_field(variants_json, default=[])
        if not isinstance(variants_data, list):
            variants_data = []
        variants = self.process_variants(variants_data)

        for i, variant in enumerate(variants):
            variant_dict = asdict(variant)
            for key, value in variant_dict.items():
                if value is not None:
                    col_name = f"Variant {key.replace('_', ' ').title()}"
                    if i == 0:
                        shopify_product[col_name] = value
                    else:
                        shopify_product[f"{col_name} {i + 1}"] = value

        images_json = product.get("images", "[]")
        image_urls = self.parse_json_field(images_json, default=[])
        if not isinstance(image_urls, list):
            image_urls = []
        processed_images = self.process_images(image_urls, str(product_id))

        for i, image in enumerate(processed_images):
            prefix = "Image Src" if i == 0 else f"Image Src {i + 1}"
            pos_key = "Image Position" if i == 0 else f"Image Position {i + 1}"
            alt_key = "Image Alt Text" if i == 0 else f"Image Alt Text {i + 1}"
            shopify_product[prefix] = image["src"]
            shopify_product[pos_key] = image["position"]
            shopify_product[alt_key] = image["alt"]

        return shopify_product

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """Load image URL mapping."""
        if "woo_url" in mapping_df.columns and "shopify_url" in mapping_df.columns:
            return dict(
                zip(
                    mapping_df["woo_url"].astype(str),
                    mapping_df["shopify_url"].astype(str),
                )
            )
        return {}

    def convert_products(
        self,
        input_file: str,
        output_file: str,
        image_mapping_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        """Convert WooCommerce products to Shopify format."""
        if image_mapping_file and Path(image_mapping_file).exists():
            with open(image_mapping_file, "r", encoding=self.config.encoding) as f:
                reader = csv.DictReader(f)
                self.image_mapping = {
                    row["woo_url"]: row["shopify_url"]
                    for row in reader
                    if "woo_url" in row and "shopify_url" in row
                }
            self.logger.info(f"Loaded {len(self.image_mapping)} image mappings")

        self.convert_data(input_file, output_file, dry_run=dry_run)
