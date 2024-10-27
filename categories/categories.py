# categories/collections.py
import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
import hashlib

class CollectionMigrationTool:
    """Tool for migrating WordPress/WooCommerce categories to Shopify collections."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.setup_logging()
        self.stats = {
            'total_collections': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'rules_created': 0
        }
        self.processed_handles = set()
        
    def setup_logging(self):
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'collection_migration_{datetime.now():%Y%m%d_%H%M%S}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_unique_handle(self, title: str) -> str:
        """Create unique URL-friendly handle from collection title."""
        base_handle = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        handle = base_handle
        
        # If handle exists, append a short hash
        counter = 1
        while handle in self.processed_handles:
            hash_suffix = hashlib.md5(f"{base_handle}{counter}".encode()).hexdigest()[:4]
            handle = f"{base_handle}-{hash_suffix}"
            counter += 1
            
        self.processed_handles.add(handle)
        return handle

    def clean_html(self, html_content: str) -> str:
        """Clean HTML content for Shopify compatibility."""
        if not html_content:
            return ""
            
        # Remove WordPress-specific shortcodes
        html_content = re.sub(r'\[[^\]]+\]', '', html_content)
        
        # Remove empty paragraphs
        html_content = re.sub(r'<p>\s*</p>', '', html_content)
        
        # Clean up whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        
        return html_content.strip()

    def extract_image_url(self, image_data: str) -> str:
        """Extract clean image URL from WordPress image data."""
        if not image_data:
            return ""
            
        try:
            # Handle JSON encoded image data
            if image_data.startswith('{'):
                img_json = json.loads(image_data)
                return img_json.get('url', '')
                
            # Handle direct URLs
            if image_data.startswith(('http://', 'https://')):
                return image_data
                
            return ""
            
        except json.JSONDecodeError:
            return image_data if image_data.startswith(('http://', 'https://')) else ""

    def create_collection_rule(self, category: pd.Series) -> Dict:
        """Create Shopify collection rules from category data."""
        rules = []
        
        # Tag-based rule
        if 'slug' in category:
            rules.append({
                'column': 'tag',
                'relation': 'equals',
                'condition': f"category_{category['slug']}"
            })
            
        # Product type rule
        if 'name' in category:
            rules.append({
                'column': 'type',
                'relation': 'equals',
                'condition': category['name']
            })
            
        return rules

    def convert_collections(self, input_file: str, output_file: str, image_mapping_file: Optional[str] = None):
        """
        Convert WordPress/WooCommerce categories to Shopify collections.
        
        Args:
            input_file: Path to WordPress categories export CSV
            output_file: Path to save Shopify collections CSV
            image_mapping_file: Optional CSV file mapping category IDs to image URLs
        """
        try:
            self.logger.info(f"Starting collection migration from {input_file}")
            
            # Load image mapping if provided
            image_mapping = {}
            if image_mapping_file:
                mapping_df = pd.read_csv(image_mapping_file)
                image_mapping = dict(zip(mapping_df['category_id'], mapping_df['image_url']))
            
            # Read WordPress categories
            df = pd.read_csv(input_file)
            self.stats['total_collections'] = len(df)
            
            shopify_collections = []
            parent_child_relations = []  # Store parent-child relationships
            
            for _, category in df.iterrows():
                try:
                    # Create collection handle
                    handle = self.create_unique_handle(category['name'])
                    
                    # Get image URL
                    image_url = (
                        image_mapping.get(category.get('term_id', ''), '') or 
                        self.extract_image_url(category.get('image', ''))
                    )
                    
                    # Create collection data
                    collection = {
                        'Handle': handle,
                        'Title': category['name'],
                        'Body HTML': self.clean_html(category.get('description', '')),
                        'Collection Type': 'smart' if self.config.get('use_smart_collections', True) else 'custom',
                        'Published': True,
                        'Image Src': image_url,
                        'Sort Order': 'best-selling',  # Can be customized
                        'Template Suffix': '',
                        'Published Scope': 'web',
                        'SEO Title': category.get('seo_title', category['name']),
                        'SEO Description': category.get('seo_description', ''),
                        'Rules': json.dumps(self.create_collection_rule(category)) if self.config.get('use_smart_collections', True) else '',
                    }
                    
                    # Store parent-child relationship if exists
                    if 'parent' in category and category['parent']:
                        parent_child_relations.append({
                            'child': handle,
                            'parent_id': category['parent']
                        })
                    
                    shopify_collections.append(collection)
                    self.stats['successful'] += 1
                    
                    if collection['Rules']:
                        self.stats['rules_created'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing category {category.get('name')}: {str(e)}")
                    self.stats['failed'] += 1
            
            # Process parent-child relationships
            for relation in parent_child_relations:
                try:
                    parent_row = df[df['term_id'] == relation['parent_id']].iloc[0]
                    parent_handle = self.create_unique_handle(parent_row['name'])
                    
                    # Add parent handle to child collection
                    child_collection = next(c for c in shopify_collections if c['Handle'] == relation['child'])
                    child_collection['Parent Handle'] = parent_handle
                    
                except Exception as e:
                    self.logger.warning(f"Could not process parent-child relationship: {str(e)}")
                    self.stats['warnings'] += 1
            
            # Save to CSV
            output_df = pd.DataFrame(shopify_collections)
            output_df.to_csv(output_file, index=False)
            
            # Generate report
            self.generate_report(output_file)
            
            self.logger.info(f"Collection migration completed. See {output_file} for results.")
            
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
            'success_rate': f"{(self.stats['successful'] / self.stats['total_collections'] * 100):.2f}%",
            'configuration': {
                'use_smart_collections': self.config.get('use_smart_collections', True),
                'image_mapping_used': bool(self.config.get('image_mapping_file'))
            }
        }
        
        # Save report
        report_file = Path('reports') / f'collection_migration_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Migration report saved to {report_file}")

def main():
    """Example usage of the CollectionMigrationTool."""
    config = {
        'input_file': 'data/input/wp_categories_export.csv',
        'output_file': 'data/output/sp_collections_import.csv',
        'image_mapping_file': 'data/input/category_images.csv',  # Optional
        'use_smart_collections': True  # Use smart collections with rules
    }
    
    tool = CollectionMigrationTool(config)
    
    try:
        tool.convert_collections(
            input_file=config['input_file'],
            output_file=config['output_file'],
            image_mapping_file=config.get('image_mapping_file')
        )
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()