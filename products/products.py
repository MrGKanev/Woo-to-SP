# products/products.py
"""Product migration module for converting WooCommerce products to Shopify format."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
from dataclasses import dataclass, asdict
import csv
from urllib.parse import urlparse
import argparse
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from base.base_migration import BaseMigrationTool


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

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize product migration tool."""
        super().__init__(config)
        self.image_mapping: Dict[str, str] = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for product migration."""
        config = super()._get_default_config()
        config.update({
            'image_migration': True,
            'inventory_tracking': True,
            'default_weight_unit': 'kg',
            'skip_drafts': False,
        })
        return config

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics for product migration."""
        stats = super()._init_stats()
        stats.update({
            'variants_processed': 0,
            'images_processed': 0,
            'drafts_skipped': 0,
        })
        return stats

    def validate_item(self, product: Any) -> Tuple[bool, List[str]]:
        """
        Validate product data before conversion.

        Args:
            product: Product data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not product.get('post_title'):
            errors.append("Missing product title")

        # Skip drafts if configured
        if self.config.get('skip_drafts') and product.get('status') == 'draft':
            self.stats['drafts_skipped'] += 1
            errors.append("Draft product skipped")

        return len(errors) == 0, errors

    def process_images(
        self,
        image_urls: List[str],
        product_id: str
    ) -> List[Dict[str, Any]]:
        """
        Process product images and prepare for Shopify import.

        Args:
            image_urls: List of image URLs
            product_id: Product ID for logging

        Returns:
            List of processed image data dictionaries
        """
        if not self.config.get('image_migration', True):
            return []

        processed_images = []

        for position, url in enumerate(image_urls, 1):
            try:
                # Clean and validate URL
                parsed_url = urlparse(url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    self.logger.warning(f"Invalid image URL for product {product_id}: {url}")
                    continue

                # Apply mapping if available
                mapped_url = self.image_mapping.get(url, url)

                image_data = {
                    'src': mapped_url,
                    'position': position,
                    'alt': f"Product image {position}"
                }

                processed_images.append(image_data)
                self.stats['images_processed'] += 1

            except Exception as e:
                self.logger.error(f"Error processing image {url} for product {product_id}: {str(e)}")

        return processed_images

    def process_variants(self, variants_data: List[Dict[str, Any]]) -> List[ProductVariant]:
        """
        Process product variants data.

        Args:
            variants_data: List of variant data dictionaries

        Returns:
            List of ProductVariant objects
        """
        processed_variants = []

        for variant_data in variants_data:
            try:
                # Get compare at price (regular price) if different from sale price
                compare_at = None
                if variant_data.get('regular_price'):
                    regular = float(variant_data['regular_price'])
                    sale = float(variant_data.get('price', 0))
                    if regular > sale:
                        compare_at = regular

                variant = ProductVariant(
                    sku=str(variant_data.get('sku', '')),
                    price=float(variant_data.get('price', 0)),
                    compare_at_price=compare_at,
                    weight=float(variant_data.get('weight', 0) or 0),
                    weight_unit=variant_data.get('weight_unit', self.config['default_weight_unit']),
                    inventory_quantity=int(variant_data.get('stock_quantity', 0) or 0),
                    option1=variant_data.get('attribute_1'),
                    option2=variant_data.get('attribute_2'),
                    option3=variant_data.get('attribute_3')
                )

                processed_variants.append(variant)
                self.stats['variants_processed'] += 1

            except Exception as e:
                self.logger.error(f"Error processing variant: {str(e)}")

        return processed_variants

    def convert_item(self, product: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a WooCommerce product to Shopify format.

        Args:
            product: Product data to convert

        Returns:
            Converted product data for Shopify
        """
        product_id = product.get('ID', 'unknown')

        # Process basic product data
        shopify_product = {
            'Handle': self.create_handle(product['post_title']),
            'Title': product['post_title'],
            'Body (HTML)': self.clean_html(str(product.get('post_content', ''))),
            'Vendor': self.clean_text(product.get('vendor', '')),
            'Type': self.clean_text(product.get('product_type', '')),
            'Tags': self.clean_text(product.get('tags', '')),
            'Published': product.get('status') == 'publish',
            'Option1 Name': product.get('attribute_1_name'),
            'Option2 Name': product.get('attribute_2_name'),
            'Option3 Name': product.get('attribute_3_name'),
        }

        # Process variants
        variants_json = product.get('variations', '[]')
        variants_data = self.parse_json_field(variants_json, default=[])
        variants = self.process_variants(variants_data)

        # Add variant data to product
        for i, variant in enumerate(variants):
            variant_dict = asdict(variant)
            for key, value in variant_dict.items():
                if value is not None:
                    col_name = f'Variant {key.replace("_", " ").title()}'
                    if i == 0:
                        shopify_product[col_name] = value
                    else:
                        shopify_product[f'{col_name} {i+1}'] = value

        # Process images
        images_json = product.get('images', '[]')
        image_urls = self.parse_json_field(images_json, default=[])
        processed_images = self.process_images(image_urls, product_id)

        # Add image data
        for i, image in enumerate(processed_images):
            shopify_product[f'Image Src' if i == 0 else f'Image Src {i+1}'] = image['src']
            shopify_product[f'Image Position' if i == 0 else f'Image Position {i+1}'] = image['position']
            shopify_product[f'Image Alt Text' if i == 0 else f'Image Alt Text {i+1}'] = image['alt']

        return shopify_product

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """
        Load image URL mapping.

        Args:
            mapping_df: DataFrame with woo_url and shopify_url columns

        Returns:
            Dictionary mapping WooCommerce URLs to Shopify URLs
        """
        if 'woo_url' in mapping_df.columns and 'shopify_url' in mapping_df.columns:
            return dict(zip(
                mapping_df['woo_url'].astype(str),
                mapping_df['shopify_url'].astype(str)
            ))
        return {}

    def convert_products(
        self,
        input_file: str,
        output_file: str,
        image_mapping_file: Optional[str] = None
    ) -> None:
        """
        Convert WooCommerce products to Shopify format.

        Args:
            input_file: Path to WooCommerce products export CSV
            output_file: Path to save Shopify products CSV
            image_mapping_file: Optional CSV file mapping WooCommerce image URLs to Shopify CDN URLs
        """
        # Load image mapping if provided
        if image_mapping_file and Path(image_mapping_file).exists():
            with open(image_mapping_file, 'r') as f:
                reader = csv.DictReader(f)
                self.image_mapping = {row['woo_url']: row['shopify_url'] for row in reader}
            self.logger.info(f"Loaded {len(self.image_mapping)} image mappings")

        # Use base class conversion
        self.convert_data(input_file, output_file)


def main():
    """CLI entry point for product migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce products to Shopify format'
    )
    parser.add_argument(
        '-i', '--input',
        default='woo_products_export.csv',
        help='Path to WooCommerce products export CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_products_import.csv',
        help='Path to save Shopify products CSV'
    )
    parser.add_argument(
        '-m', '--image-mapping',
        default=None,
        help='Path to image mapping CSV (optional)'
    )
    parser.add_argument(
        '--skip-drafts',
        action='store_true',
        help='Skip draft products'
    )
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Disable image migration'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    config = {
        'image_migration': not args.no_images,
        'skip_drafts': args.skip_drafts,
        'show_progress': not args.no_progress,
    }

    tool = ProductMigrationTool(config)

    try:
        tool.convert_products(
            input_file=args.input,
            output_file=args.output,
            image_mapping_file=args.image_mapping
        )
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
