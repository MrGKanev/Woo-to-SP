# products/products.py
"""Product migration module for converting WooCommerce products to Shopify format."""

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import json
from typing import Dict, List, Optional, Any
import re
from dataclasses import dataclass, asdict
import csv
from urllib.parse import urlparse
import argparse

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

class ProductMigrationTool:
    """Tool for migrating WooCommerce products to Shopify."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'image_migration': True,
            'inventory_tracking': True,
            'default_weight_unit': 'kg',
            'batch_size': 100,
            'skip_drafts': False
        }
        self.setup_logging()
        self.stats = {
            'total_products': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'variants_processed': 0,
            'images_processed': 0
        }
        
    def setup_logging(self):
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'product_migration_{datetime.now():%Y%m%d_%H%M%S}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def clean_html(self, html_content: str) -> str:
        """Clean HTML content while preserving basic formatting."""
        if not html_content:
            return ""
            
        # Convert common HTML entities
        html_content = html_content.replace('&nbsp;', ' ')
        html_content = html_content.replace('&amp;', '&')
        html_content = html_content.replace('&quot;', '"')
        
        # Remove script and style elements
        html_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style.*?</style>', '', html_content, flags=re.DOTALL)
        
        # Preserve line breaks and paragraphs
        html_content = html_content.replace('</p>', '</p>\n')
        html_content = html_content.replace('<br', '\n<br')
        
        # Remove remaining HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        
        return html_content.strip()

    def create_handle(self, title: str) -> str:
        """Create URL-friendly handle from product title."""
        handle = title.lower()
        handle = re.sub(r'[^a-z0-9]+', '-', handle)
        return handle.strip('-')

    def process_images(self, image_urls: List[str], product_id: str) -> List[Dict[str, str]]:
        """Process product images and prepare for Shopify import."""
        processed_images = []
        
        for position, url in enumerate(image_urls, 1):
            try:
                # Clean and validate URL
                parsed_url = urlparse(url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    self.logger.warning(f"Invalid image URL for product {product_id}: {url}")
                    continue
                
                image_data = {
                    'src': url,
                    'position': position,
                    'alt': f"Product image {position}"
                }
                
                processed_images.append(image_data)
                self.stats['images_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing image {url} for product {product_id}: {str(e)}")
                
        return processed_images

    def process_variants(self, variants_data: List[Dict[str, Any]]) -> List[ProductVariant]:
        """Process product variants data."""
        processed_variants = []
        
        for variant_data in variants_data:
            try:
                variant = ProductVariant(
                    sku=variant_data.get('sku', ''),
                    price=float(variant_data.get('price', 0)),
                    compare_at_price=float(variant_data.get('regular_price', 0)) 
                        if variant_data.get('regular_price') else None,
                    weight=float(variant_data.get('weight', 0)),
                    weight_unit=variant_data.get('weight_unit', self.config['default_weight_unit']),
                    inventory_quantity=int(variant_data.get('stock_quantity', 0)),
                    option1=variant_data.get('attribute_1'),
                    option2=variant_data.get('attribute_2'),
                    option3=variant_data.get('attribute_3')
                )
                
                processed_variants.append(variant)
                self.stats['variants_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing variant: {str(e)}")
                
        return processed_variants

    def convert_products(self, input_file: str, output_file: str, image_mapping_file: Optional[str] = None):
        """
        Convert WooCommerce products to Shopify format.
        
        Args:
            input_file: Path to WooCommerce products export CSV
            output_file: Path to save Shopify products CSV
            image_mapping_file: Optional CSV file mapping WooCommerce image URLs to Shopify CDN URLs
        """
        try:
            self.logger.info(f"Starting product migration from {input_file}")
            
            # Load image mapping if provided
            image_mapping = {}
            if image_mapping_file:
                with open(image_mapping_file, 'r') as f:
                    reader = csv.DictReader(f)
                    image_mapping = {row['woo_url']: row['shopify_url'] for row in reader}
            
            # Read WooCommerce products
            df = pd.read_csv(input_file)
            self.stats['total_products'] = len(df)
            
            shopify_products = []
            
            for _, product in df.iterrows():
                try:
                    # Skip draft products if configured
                    if self.config['skip_drafts'] and product.get('status') == 'draft':
                        continue
                    
                    # Process basic product data
                    shopify_product = {
                        'Handle': self.create_handle(product['post_title']),
                        'Title': product['post_title'],
                        'Body (HTML)': self.clean_html(product['post_content']),
                        'Vendor': product.get('vendor', ''),
                        'Type': product.get('product_type', ''),
                        'Tags': product.get('tags', ''),
                        'Published': product.get('status') == 'publish',
                        'Option1 Name': product.get('attribute_1_name'),
                        'Option2 Name': product.get('attribute_2_name'),
                        'Option3 Name': product.get('attribute_3_name'),
                    }
                    
                    # Process variants
                    variants_data = json.loads(product.get('variations', '[]'))
                    variants = self.process_variants(variants_data)
                    
                    # Add variant data to product
                    for i, variant in enumerate(variants):
                        variant_dict = asdict(variant)
                        for key, value in variant_dict.items():
                            if value is not None:
                                shopify_product[f'Variant {i+1} {key.title()}'] = value
                    
                    # Process images
                    image_urls = json.loads(product.get('images', '[]'))
                    processed_images = self.process_images(image_urls, product['ID'])
                    
                    # Add image data
                    for i, image in enumerate(processed_images):
                        shopify_product[f'Image {i+1} Src'] = image_mapping.get(image['src'], image['src'])
                        shopify_product[f'Image {i+1} Position'] = image['position']
                        shopify_product[f'Image {i+1} Alt Text'] = image['alt']
                    
                    shopify_products.append(shopify_product)
                    self.stats['successful'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing product {product.get('ID')}: {str(e)}")
                    self.stats['failed'] += 1
            
            # Save to CSV
            if shopify_products:
                output_df = pd.DataFrame(shopify_products)
                output_df.to_csv(output_file, index=False)
                
                # Generate report
                self.generate_report(output_file)
                
                self.logger.info(f"Product migration completed. See {output_file} for results.")
            else:
                self.logger.warning("No products were successfully processed!")
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

    def generate_report(self, output_file: str) -> None:
        """Generate migration report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'input_file': self.config.get('input_file', 'N/A'),
            'output_file': output_file,
            'statistics': self.stats,
            'success_rate': f"{(self.stats['successful'] / max(self.stats['total_products'], 1) * 100):.2f}%",
            'configuration': self.config
        }
        
        # Save report
        report_file = Path('reports') / f'product_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Migration report saved to {report_file}")

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

    args = parser.parse_args()

    config = {
        'image_migration': not args.no_images,
        'inventory_tracking': True,
        'default_weight_unit': 'kg',
        'batch_size': 100,
        'skip_drafts': args.skip_drafts
    }

    tool = ProductMigrationTool(config)

    try:
        tool.convert_products(
            input_file=args.input,
            output_file=args.output,
            image_mapping_file=args.image_mapping
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()