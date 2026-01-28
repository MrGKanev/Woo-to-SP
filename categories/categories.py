# categories/categories.py
"""Categories/Collections migration module for converting WooCommerce categories to Shopify collections."""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import hashlib
import argparse
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from base.base_migration import BaseMigrationTool


class CollectionMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce categories to Shopify collections."""

    TOOL_NAME = "collection"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize collection migration tool."""
        super().__init__(config)
        self.processed_handles: set = set()
        self.image_mapping: Dict[str, str] = {}
        self.parent_relations: List[Dict[str, Any]] = []

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for collection migration."""
        config = super()._get_default_config()
        config.update({
            'use_smart_collections': True,
            'default_sort_order': 'best-selling',
        })
        return config

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics for collection migration."""
        stats = super()._init_stats()
        stats.update({
            'rules_created': 0,
            'images_processed': 0,
            'parent_relations': 0,
        })
        return stats

    def validate_item(self, category: Any) -> Tuple[bool, List[str]]:
        """
        Validate category data before conversion.

        Args:
            category: Category data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if not category.get('name'):
            errors.append("Missing category name")

        return len(errors) == 0, errors

    def create_unique_handle(self, title: str) -> str:
        """
        Create unique URL-friendly handle from collection title.

        Args:
            title: Collection title

        Returns:
            Unique URL-friendly handle
        """
        base_handle = self.create_handle(title)
        handle = base_handle

        # If handle exists, append a short hash
        counter = 1
        while handle in self.processed_handles:
            hash_suffix = hashlib.md5(f"{base_handle}{counter}".encode()).hexdigest()[:4]
            handle = f"{base_handle}-{hash_suffix}"
            counter += 1

        self.processed_handles.add(handle)
        return handle

    def extract_image_url(self, image_data: Any) -> str:
        """
        Extract clean image URL from WordPress image data.

        Args:
            image_data: Image data (URL, JSON string, or dict)

        Returns:
            Clean image URL string
        """
        if not image_data or pd.isna(image_data):
            return ""

        image_str = str(image_data)

        # Handle JSON encoded image data
        if image_str.startswith('{'):
            try:
                img_json = json.loads(image_str)
                return img_json.get('url', '')
            except json.JSONDecodeError:
                pass

        # Handle direct URLs
        if image_str.startswith(('http://', 'https://')):
            return image_str

        return ""

    def create_collection_rules(self, category: Any) -> List[Dict[str, str]]:
        """
        Create Shopify collection rules from category data.

        Args:
            category: Category data

        Returns:
            List of rule dictionaries
        """
        rules = []

        # Tag-based rule using slug
        if category.get('slug'):
            rules.append({
                'column': 'tag',
                'relation': 'equals',
                'condition': f"category_{category['slug']}"
            })
            self.stats['rules_created'] += 1

        # Product type rule using name
        if category.get('name'):
            rules.append({
                'column': 'type',
                'relation': 'equals',
                'condition': category['name']
            })
            self.stats['rules_created'] += 1

        return rules

    def convert_item(self, category: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a WooCommerce category to Shopify collection format.

        Args:
            category: Category data to convert

        Returns:
            Converted collection data for Shopify
        """
        # Create unique handle
        handle = self.create_unique_handle(category['name'])

        # Get image URL from mapping or extract from data
        image_url = self.image_mapping.get(
            str(category.get('term_id', '')),
            self.extract_image_url(category.get('image', ''))
        )

        if image_url:
            self.stats['images_processed'] += 1

        # Create collection rules if smart collections enabled
        rules = []
        if self.config.get('use_smart_collections', True):
            rules = self.create_collection_rules(category)

        # Create collection data
        collection = {
            'Handle': handle,
            'Title': category['name'],
            'Body HTML': self.clean_html(str(category.get('description', ''))),
            'Collection Type': 'smart' if self.config.get('use_smart_collections', True) else 'custom',
            'Published': True,
            'Image Src': image_url,
            'Sort Order': self.config.get('default_sort_order', 'best-selling'),
            'Template Suffix': '',
            'Published Scope': 'web',
            'SEO Title': self.clean_text(category.get('seo_title', category['name'])),
            'SEO Description': self.clean_text(category.get('seo_description', '')),
            'Rules': json.dumps(rules) if rules else '',
        }

        # Track parent-child relationship
        if category.get('parent') and not pd.isna(category.get('parent')):
            self.parent_relations.append({
                'child_handle': handle,
                'parent_id': category['parent']
            })
            self.stats['parent_relations'] += 1

        return collection

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """
        Load category ID to image URL mapping.

        Args:
            mapping_df: DataFrame with category_id and image_url columns

        Returns:
            Dictionary mapping category IDs to image URLs
        """
        if 'category_id' in mapping_df.columns and 'image_url' in mapping_df.columns:
            return dict(zip(
                mapping_df['category_id'].astype(str),
                mapping_df['image_url'].astype(str)
            ))
        return {}

    def convert_collections(
        self,
        input_file: str,
        output_file: str,
        image_mapping_file: Optional[str] = None
    ) -> None:
        """
        Convert WooCommerce categories to Shopify collections.

        Args:
            input_file: Path to WordPress categories export CSV
            output_file: Path to save Shopify collections CSV
            image_mapping_file: Optional CSV mapping category IDs to image URLs
        """
        # Load image mapping if provided
        if image_mapping_file and Path(image_mapping_file).exists():
            mapping_df = pd.read_csv(image_mapping_file)
            self.image_mapping = self.load_mapping(mapping_df)
            self.logger.info(f"Loaded {len(self.image_mapping)} image mappings")

        # Use base class conversion
        self.convert_data(input_file, output_file)

        # Log additional stats
        if self.parent_relations:
            self.logger.info(f"Found {len(self.parent_relations)} parent-child relationships")


def main():
    """CLI entry point for collection migration."""
    parser = argparse.ArgumentParser(
        description='Migrate WooCommerce categories to Shopify collections'
    )
    parser.add_argument(
        '-i', '--input',
        default='wp_categories_export.csv',
        help='Path to WordPress categories export CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='shopify_collections_import.csv',
        help='Path to save Shopify collections CSV'
    )
    parser.add_argument(
        '-m', '--image-mapping',
        default=None,
        help='Path to category images mapping CSV (optional)'
    )
    parser.add_argument(
        '--manual-collections',
        action='store_true',
        help='Use manual collections instead of smart collections'
    )
    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    args = parser.parse_args()

    config = {
        'use_smart_collections': not args.manual_collections,
        'show_progress': not args.no_progress,
    }

    tool = CollectionMigrationTool(config)

    try:
        tool.convert_collections(
            input_file=args.input,
            output_file=args.output,
            image_mapping_file=args.image_mapping
        )
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
