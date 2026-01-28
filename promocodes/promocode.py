# promocodes/promocode.py
"""Discount codes migration module for converting WooCommerce coupons to Shopify discount codes."""

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import json
from typing import Dict, List, Optional, Tuple
import re
import argparse

class DiscountMigrationTool:
    """Tool for migrating WordPress/WooCommerce coupons to Shopify discount codes."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'default_minimum_amount': 0,
            'default_usage_limit': None,
            'batch_size': 500
        }
        self.setup_logging()
        self.stats = {
            'total_coupons': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0
        }

    def setup_logging(self):
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'discount_migration_{datetime.now():%Y%m%d_%H%M%S}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def clean_discount_code(self, code: str) -> str:
        """Clean and validate discount code."""
        if not code:
            return ""
        
        # Remove special characters and spaces
        code = re.sub(r'[^A-Z0-9_-]', '', code.upper())
        
        # Ensure code meets Shopify requirements
        if len(code) > 50:
            code = code[:50]
            
        return code

    def convert_amount_type(self, woo_type: str, amount: float) -> Tuple[str, float]:
        """Convert WooCommerce discount type to Shopify format."""
        if woo_type == 'percent':
            return 'percentage', amount
        elif woo_type in ['fixed_cart', 'fixed_product']:
            return 'fixed_amount', amount
        else:
            return 'percentage', amount  # Default to percentage

    def format_date(self, date_str: str) -> str:
        """Format date to Shopify's expected format."""
        if not date_str:
            return ""
            
        try:
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            return ""
        except Exception:
            return ""

    def process_product_restrictions(self, included_products: str, excluded_products: str) -> Dict:
        """Process product restrictions for Shopify format."""
        restrictions = {
            'entitled_product_ids': [],
            'excluded_product_ids': []
        }
        
        if included_products:
            try:
                restrictions['entitled_product_ids'] = [
                    str(id).strip() for id in included_products.split(',')
                ]
            except Exception:
                pass
                
        if excluded_products:
            try:
                restrictions['excluded_product_ids'] = [
                    str(id).strip() for id in excluded_products.split(',')
                ]
            except Exception:
                pass
                
        return restrictions

    def convert_discounts(self, input_file: str, output_file: str, product_mapping_file: Optional[str] = None):
        """
        Convert WooCommerce coupons to Shopify discount codes.
        
        Args:
            input_file: Path to WooCommerce coupons export CSV
            output_file: Path to save Shopify discount codes CSV
            product_mapping_file: Optional CSV file mapping WooCommerce product IDs to Shopify IDs
        """
        try:
            self.logger.info(f"Starting discount code migration from {input_file}")
            
            # Load product mapping if provided
            product_mapping = {}
            if product_mapping_file:
                mapping_df = pd.read_csv(product_mapping_file)
                product_mapping = dict(zip(mapping_df['woo_id'], mapping_df['shopify_id']))
            
            # Read WooCommerce coupons
            df = pd.read_csv(input_file)
            self.stats['total_coupons'] = len(df)
            
            shopify_discounts = []
            
            for _, coupon in df.iterrows():
                try:
                    # Clean and validate discount code
                    code = self.clean_discount_code(coupon['code'])
                    if not code:
                        self.logger.warning(f"Invalid coupon code: {coupon['code']}")
                        self.stats['warnings'] += 1
                        continue
                    
                    # Convert discount type and amount
                    discount_type, amount = self.convert_amount_type(
                        coupon.get('discount_type', 'percent'),
                        float(coupon.get('amount', 0))
                    )
                    
                    # Process product restrictions
                    restrictions = self.process_product_restrictions(
                        coupon.get('product_ids', ''),
                        coupon.get('exclude_product_ids', '')
                    )
                    
                    # Create Shopify discount
                    shopify_discount = {
                        'Discount Code': code,
                        'Type': discount_type,
                        'Amount': amount,
                        'Minimum Purchase Amount': coupon.get('minimum_amount', self.config['default_minimum_amount']),
                        'Starts At': self.format_date(coupon.get('date_created', '')),
                        'Ends At': self.format_date(coupon.get('date_expires', '')),
                        'Usage Limit': coupon.get('usage_limit', self.config['default_usage_limit']),
                        'Once Per Customer': coupon.get('individual_use', 'no') == 'yes',
                        'Status': 'enabled' if coupon.get('enabled', 'yes') == 'yes' else 'disabled',
                        'Applies To': 'all' if not restrictions['entitled_product_ids'] else 'specific',
                        'Products': ','.join(restrictions['entitled_product_ids']),
                        'Excluded Products': ','.join(restrictions['excluded_product_ids']),
                        'Description': coupon.get('description', ''),
                        'Times Used': coupon.get('usage_count', 0)
                    }
                    
                    shopify_discounts.append(shopify_discount)
                    self.stats['successful'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing coupon {coupon.get('code')}: {str(e)}")
                    self.stats['failed'] += 1
            
            # Save to CSV
            if shopify_discounts:
                output_df = pd.DataFrame(shopify_discounts)
                output_df.to_csv(output_file, index=False)
                
                # Generate report
                self.generate_report(output_file)
                
                self.logger.info(f"Discount code migration completed. See {output_file} for results.")
            else:
                self.logger.warning("No discount codes were successfully processed!")
            
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
            'success_rate': f"{(self.stats['successful'] / max(self.stats['total_coupons'], 1) * 100):.2f}%",
            'configuration': self.config
        }
        
        # Save report
        report_file = Path('reports') / f'discount_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Migration report saved to {report_file}")

def main():
    """CLI entry point for discount code migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce coupons to Shopify discount codes'
    )
    parser.add_argument(
        '-i', '--input',
        default='wp_coupons_export.csv',
        help='Path to WooCommerce coupons export CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_discounts_import.csv',
        help='Path to save Shopify discount codes CSV'
    )
    parser.add_argument(
        '-m', '--product-mapping',
        default=None,
        help='Path to product mapping CSV (optional)'
    )
    parser.add_argument(
        '--min-amount',
        type=float,
        default=0,
        help='Default minimum purchase amount'
    )

    args = parser.parse_args()

    config = {
        'default_minimum_amount': args.min_amount,
        'default_usage_limit': None,
        'batch_size': 500
    }

    tool = DiscountMigrationTool(config)

    try:
        tool.convert_discounts(
            input_file=args.input,
            output_file=args.output,
            product_mapping_file=args.product_mapping
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()