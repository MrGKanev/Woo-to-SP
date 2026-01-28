# reviews/review.py
"""Review migration module for converting WooCommerce product reviews to Shopify format."""

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
import re
from typing import Dict, List, Optional, Tuple
import json
import argparse

class ReviewMigrationTool:
    """Tool for migrating WooCommerce product reviews to Shopify."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.setup_logging()
        self.stats = {
            'total_reviews': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0
        }
        
    def setup_logging(self):
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'review_migration_{datetime.now():%Y%m%d_%H%M%S}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def validate_review(self, review: Dict) -> Tuple[bool, List[str]]:
        """
        Validate review data before conversion.
        Returns tuple of (is_valid, list of errors).
        """
        errors = []
        
        # Check required fields
        required_fields = ['comment_ID', 'comment_post_ID', 'comment_author', 'comment_content']
        for field in required_fields:
            if not review.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate rating if present
        if 'rating' in review:
            try:
                rating = int(review['rating'])
                if not 1 <= rating <= 5:
                    errors.append("Rating must be between 1 and 5")
            except (ValueError, TypeError):
                errors.append("Invalid rating format")
        
        return len(errors) == 0, errors

    def clean_review_text(self, text: str) -> str:
        """Clean and format review text."""
        if not text:
            return ""
            
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text

    def format_date(self, date_str: str) -> str:
        """Format date to Shopify's expected format."""
        try:
            # Handle different date formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            raise ValueError(f"Unrecognized date format: {date_str}")
        except Exception as e:
            self.logger.warning(f"Date formatting error: {str(e)}. Using current date.")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def convert_reviews(self, input_file: str, output_file: str, product_mapping_file: Optional[str] = None):
        """
        Convert WooCommerce reviews to Shopify format.
        
        Args:
            input_file: Path to WooCommerce reviews export CSV
            output_file: Path to save Shopify reviews CSV
            product_mapping_file: Optional CSV file mapping WooCommerce product IDs to Shopify handles
        """
        try:
            self.logger.info(f"Starting review migration from {input_file}")
            
            # Load product mapping if provided
            product_mapping = {}
            if product_mapping_file:
                mapping_df = pd.read_csv(product_mapping_file)
                product_mapping = dict(zip(mapping_df['woo_id'], mapping_df['shopify_handle']))
            
            # Read WooCommerce reviews
            df = pd.read_csv(input_file)
            self.stats['total_reviews'] = len(df)
            
            shopify_reviews = []
            
            for _, review in df.iterrows():
                try:
                    # Validate review data
                    is_valid, errors = self.validate_review(review)
                    if not is_valid:
                        self.logger.warning(f"Invalid review {review.get('comment_ID')}: {', '.join(errors)}")
                        self.stats['warnings'] += 1
                        continue
                    
                    # Get product handle
                    product_id = str(review['comment_post_ID'])
                    product_handle = product_mapping.get(product_id, self.create_handle(str(product_id)))
                    
                    # Convert review to Shopify format
                    shopify_review = {
                        'Product Handle': product_handle,
                        'Review Date': self.format_date(review['comment_date']),
                        'Reviewer Name': review['comment_author'],
                        'Reviewer Email': review.get('comment_author_email', ''),
                        'Review Title': review.get('title', ''),
                        'Rating': int(review.get('rating', 5)),
                        'Review Text': self.clean_review_text(review['comment_content']),
                        'Review Status': 'published' if review.get('comment_approved', '1') == '1' else 'unpublished',
                        'Reviewer Location': review.get('comment_author_location', ''),
                        'Verified Buyer': review.get('verified', '0') == '1',
                    }
                    
                    shopify_reviews.append(shopify_review)
                    self.stats['successful'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing review {review.get('comment_ID')}: {str(e)}")
                    self.stats['failed'] += 1
            
            # Save to CSV
            output_df = pd.DataFrame(shopify_reviews)
            output_df.to_csv(output_file, index=False)
            
            # Generate report
            self.generate_report(output_file)
            
            self.logger.info(f"Review migration completed. See {output_file} for results.")
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

    def create_handle(self, text: str) -> str:
        """Create URL-friendly handle."""
        handle = text.lower()
        handle = re.sub(r'[^a-z0-9]+', '-', handle)
        return handle.strip('-')

    def generate_report(self, output_file: str) -> None:
        """Generate migration report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'input_file': self.config.get('input_file', 'N/A'),
            'output_file': output_file,
            'statistics': self.stats,
            'success_rate': f"{(self.stats['successful'] / max(self.stats['total_reviews'], 1) * 100):.2f}%"
        }
        
        # Save report
        report_file = Path('reports') / f'review_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Migration report saved to {report_file}")

def main():
    """CLI entry point for review migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce product reviews to Shopify format'
    )
    parser.add_argument(
        '-i', '--input',
        default='woo_reviews_export.csv',
        help='Path to WooCommerce reviews export CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_reviews_import.csv',
        help='Path to save Shopify reviews CSV'
    )
    parser.add_argument(
        '-m', '--product-mapping',
        default=None,
        help='Path to product mapping CSV (optional)'
    )

    args = parser.parse_args()

    tool = ReviewMigrationTool()

    try:
        tool.convert_reviews(
            input_file=args.input,
            output_file=args.output,
            product_mapping_file=args.product_mapping
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()