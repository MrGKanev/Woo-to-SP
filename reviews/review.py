# reviews/review.py
"""Review migration module for converting WooCommerce product reviews to Shopify format."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import argparse
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from base.base_migration import BaseMigrationTool


class ReviewMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce product reviews to Shopify."""

    TOOL_NAME = "review"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize review migration tool."""
        super().__init__(config)
        self.product_mapping: Dict[str, str] = {}

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for review migration."""
        config = super()._get_default_config()
        config.update({
            'validate_ratings': True,
            'default_rating': 5,
        })
        return config

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics for review migration."""
        stats = super()._init_stats()
        stats.update({
            'reviews_with_missing_product': 0,
        })
        return stats

    def validate_item(self, review: Any) -> Tuple[bool, List[str]]:
        """
        Validate review data before conversion.

        Args:
            review: Review data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check required fields
        required_fields = ['comment_ID', 'comment_post_ID', 'comment_author', 'comment_content']
        for field in required_fields:
            if not review.get(field):
                errors.append(f"Missing required field: {field}")

        # Validate rating if present and validation enabled
        if self.config.get('validate_ratings', True) and 'rating' in review:
            try:
                rating = int(review['rating'])
                if not 1 <= rating <= 5:
                    errors.append("Rating must be between 1 and 5")
            except (ValueError, TypeError):
                errors.append("Invalid rating format")

        return len(errors) == 0, errors

    def convert_item(self, review: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a WooCommerce review to Shopify format.

        Args:
            review: Review data to convert

        Returns:
            Converted review data for Shopify
        """
        # Get product handle from mapping or create from ID
        product_id = str(review['comment_post_ID'])
        product_handle = self.product_mapping.get(
            product_id,
            self.create_handle(product_id)
        )

        if product_id not in self.product_mapping:
            self.stats['reviews_with_missing_product'] += 1

        # Get rating with fallback to default
        try:
            rating = int(review.get('rating', self.config['default_rating']))
            rating = max(1, min(5, rating))  # Clamp to 1-5
        except (ValueError, TypeError):
            rating = self.config['default_rating']

        # Convert to Shopify format
        return {
            'Product Handle': product_handle,
            'Review Date': self.format_date(review.get('comment_date', '')),
            'Reviewer Name': self.clean_text(review['comment_author']),
            'Reviewer Email': self.clean_text(review.get('comment_author_email', '')),
            'Review Title': self.clean_text(review.get('title', '')),
            'Rating': rating,
            'Review Text': self.clean_html(str(review['comment_content'])),
            'Review Status': 'published' if str(review.get('comment_approved', '1')) == '1' else 'unpublished',
            'Reviewer Location': self.clean_text(review.get('comment_author_location', '')),
            'Verified Buyer': str(review.get('verified', '0')) == '1',
        }

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """
        Load product ID to handle mapping.

        Args:
            mapping_df: DataFrame with woo_id and shopify_handle columns

        Returns:
            Dictionary mapping WooCommerce IDs to Shopify handles
        """
        if 'woo_id' in mapping_df.columns and 'shopify_handle' in mapping_df.columns:
            return dict(zip(
                mapping_df['woo_id'].astype(str),
                mapping_df['shopify_handle'].astype(str)
            ))
        return {}

    def convert_reviews(
        self,
        input_file: str,
        output_file: str,
        product_mapping_file: Optional[str] = None
    ) -> None:
        """
        Convert WooCommerce reviews to Shopify format.

        Args:
            input_file: Path to WooCommerce reviews export CSV
            output_file: Path to save Shopify reviews CSV
            product_mapping_file: Optional CSV mapping WooCommerce product IDs to Shopify handles
        """
        # Load product mapping if provided
        if product_mapping_file and Path(product_mapping_file).exists():
            mapping_df = pd.read_csv(product_mapping_file)
            self.product_mapping = self.load_mapping(mapping_df)
            self.logger.info(f"Loaded {len(self.product_mapping)} product mappings")

        # Use base class conversion
        self.convert_data(input_file, output_file)


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
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    config = {
        'show_progress': not args.no_progress,
    }

    tool = ReviewMigrationTool(config)

    try:
        tool.convert_reviews(
            input_file=args.input,
            output_file=args.output,
            product_mapping_file=args.product_mapping
        )
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
