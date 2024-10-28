# zerno_config.py

from typing import Dict, List, Optional
import re

class ZernoOrderTransform:
    """Specialized transformation configuration for Zerno orders."""
    
    def __init__(self):
        # Meta fields that should become separate line items
        self.separate_items = {
            'pa_burr-set': {
                'name_suffix': 'Burr Set',
                'sku_prefix': 'burr-set-',
                'price_field': 'burr_price'
            },
            'pa_cap-style': {
                'name_suffix': 'Cap',
                'sku_prefix': 'cap-style-',
                'price_field': 'cap_price'
            }
        }
        
        # Meta fields that should stay as variants
        self.variant_attributes = ['pa_color', 'pa_motor']
        
        # Additional add-on mappings
        self.addon_mappings = {
            'Accent Piece': {
                'name_suffix': 'Accent Piece',
                'sku_prefix': 'accent-piece-',
                'price_field': 'accent_price'
            },
            'Optional Add-ons': {
                'name_suffix': 'Add-on',
                'sku_prefix': 'addon-',
                'price_field': 'addon_price'
            }
        }

    def extract_meta_items(self, line_item: str) -> List[Dict]:
        """Extract meta items that should become separate line items."""
        meta_items = []
        
        # Extract all meta fields
        meta_matches = re.finditer(r'meta:([^:]+):([^|]+)', line_item)
        base_name = re.search(r'name:([^|]+)', line_item)
        base_product_name = base_name.group(1) if base_name else "Product"
        
        for match in meta_matches:
            meta_key = match.group(1)
            meta_value = match.group(2).strip()
            
            # Check if this meta field should be a separate item
            if meta_key in self.separate_items:
                config = self.separate_items[meta_key]
                item = {
                    'name': f"{meta_value} {config['name_suffix']}",
                    'sku': f"{config['sku_prefix']}{meta_value.lower().replace(' ', '-')}",
                    'price_field': config['price_field'],
                    'requires_shipping': True,
                    'taxable': True,
                    'quantity': 1,
                    'parent_name': base_product_name
                }
                meta_items.append(item)
                
        return meta_items

    def should_keep_variant(self, meta_key: str) -> bool:
        """Check if a meta field should be kept as a variant."""
        return meta_key in self.variant_attributes

    def process_addons(self, meta_str: str) -> List[Dict]:
        """Process any additional add-ons in the order."""
        addons = []
        
        for addon_key, config in self.addon_mappings.items():
            addon_match = re.search(f'meta:{addon_key}:([^|]+)', meta_str)
            if addon_match:
                value = addon_match.group(1).strip()
                addon = {
                    'name': f"{value} {config['name_suffix']}",
                    'sku': f"{config['sku_prefix']}{value.lower().replace(' ', '-')}",
                    'price_field': config['price_field'],
                    'requires_shipping': True,
                    'taxable': True,
                    'quantity': 1
                }
                addons.append(addon)
                
        return addons

def get_transform_config() -> ZernoOrderTransform:
    """Get the Zerno-specific transformation configuration."""
    return ZernoOrderTransform()