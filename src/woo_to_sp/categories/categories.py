"""Categories/Collections migration module for converting WooCommerce categories to Shopify collections."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.config import CollectionConfig


class CollectionMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce categories to Shopify collections."""

    TOOL_NAME = "collection"
    REQUIRED_COLUMNS = ["name"]

    def __init__(self, config: Optional[CollectionConfig] = None):
        super().__init__(config)
        self.processed_handles: set = set()
        self.image_mapping: Dict[str, str] = {}
        self.parent_relations: List[Dict[str, Any]] = []

    def _get_default_config(self) -> CollectionConfig:
        return CollectionConfig()

    def _init_stats(self) -> Dict[str, Any]:
        stats = super()._init_stats()
        stats.update({
            "rules_created": 0,
            "images_processed": 0,
            "parent_relations": 0,
        })
        return stats

    def validate_item(self, category: Any) -> Tuple[bool, List[str]]:
        errors = []

        if not category.get("name"):
            errors.append("Missing category name")

        return len(errors) == 0, errors

    def create_unique_handle(self, title: str) -> str:
        """Create unique URL-friendly handle from collection title."""
        base_handle = self.create_handle(title)
        handle = base_handle

        counter = 1
        while handle in self.processed_handles:
            hash_suffix = hashlib.md5(
                f"{base_handle}{counter}".encode()
            ).hexdigest()[:4]
            handle = f"{base_handle}-{hash_suffix}"
            counter += 1

        self.processed_handles.add(handle)
        return handle

    def extract_image_url(self, image_data: Any) -> str:
        """Extract clean image URL from WordPress image data."""
        if not image_data or pd.isna(image_data):
            return ""

        image_str = str(image_data)

        if image_str.startswith("{"):
            try:
                img_json = json.loads(image_str)
                return img_json.get("url", "")
            except json.JSONDecodeError:
                pass

        if image_str.startswith(("http://", "https://")):
            return image_str

        return ""

    def create_collection_rules(self, category: Any) -> List[Dict[str, str]]:
        """Create Shopify collection rules from category data."""
        rules = []

        if category.get("slug"):
            rules.append({
                "column": "tag",
                "relation": "equals",
                "condition": f"category_{category['slug']}",
            })
            self.stats["rules_created"] += 1

        if category.get("name"):
            rules.append({
                "column": "type",
                "relation": "equals",
                "condition": category["name"],
            })
            self.stats["rules_created"] += 1

        return rules

    def convert_item(self, category: Any) -> Optional[Dict[str, Any]]:
        handle = self.create_unique_handle(category["name"])

        image_url = self.image_mapping.get(
            str(category.get("term_id", "")),
            self.extract_image_url(category.get("image", "")),
        )

        if image_url:
            self.stats["images_processed"] += 1

        rules = []
        if self.config.use_smart_collections:
            rules = self.create_collection_rules(category)

        collection = {
            "Handle": handle,
            "Title": category["name"],
            "Body HTML": self.clean_html(str(category.get("description", ""))),
            "Collection Type": "smart" if self.config.use_smart_collections else "custom",
            "Published": True,
            "Image Src": image_url,
            "Sort Order": self.config.default_sort_order,
            "Template Suffix": "",
            "Published Scope": "web",
            "SEO Title": self.clean_text(
                category.get("seo_title", category["name"])
            ),
            "SEO Description": self.clean_text(
                category.get("seo_description", "")
            ),
            "Rules": json.dumps(rules) if rules else "",
        }

        if category.get("parent") and not pd.isna(category.get("parent")):
            self.parent_relations.append({
                "child_handle": handle,
                "parent_id": category["parent"],
            })
            self.stats["parent_relations"] += 1

        return collection

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """Load category ID to image URL mapping."""
        if "category_id" in mapping_df.columns and "image_url" in mapping_df.columns:
            return dict(
                zip(
                    mapping_df["category_id"].astype(str),
                    mapping_df["image_url"].astype(str),
                )
            )
        return {}

    def convert_collections(
        self,
        input_file: str,
        output_file: str,
        image_mapping_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        """Convert WooCommerce categories to Shopify collections."""
        if image_mapping_file and Path(image_mapping_file).exists():
            mapping_df = pd.read_csv(
                image_mapping_file, encoding=self.config.encoding
            )
            self.image_mapping = self.load_mapping(mapping_df)
            self.logger.info(f"Loaded {len(self.image_mapping)} image mappings")

        self.convert_data(input_file, output_file, dry_run=dry_run)

        if self.parent_relations:
            self.logger.info(
                f"Found {len(self.parent_relations)} parent-child relationships"
            )
