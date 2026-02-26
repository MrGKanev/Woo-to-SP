"""Review migration module for converting WooCommerce product reviews to Shopify format."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from woo_to_sp.base.base_migration import BaseMigrationTool
from woo_to_sp.config import ReviewConfig


class ReviewMigrationTool(BaseMigrationTool):
    """Tool for migrating WooCommerce product reviews to Shopify."""

    TOOL_NAME = "review"
    REQUIRED_COLUMNS = ["comment_ID", "comment_post_ID", "comment_author", "comment_content"]

    def __init__(self, config: Optional[ReviewConfig] = None):
        super().__init__(config)
        self.product_mapping: Dict[str, str] = {}

    def _get_default_config(self) -> ReviewConfig:
        return ReviewConfig()

    def _init_stats(self) -> Dict[str, Any]:
        stats = super()._init_stats()
        stats.update({
            "reviews_with_missing_product": 0,
        })
        return stats

    def validate_item(self, review: Any) -> Tuple[bool, List[str]]:
        errors = []

        required_fields = [
            "comment_ID",
            "comment_post_ID",
            "comment_author",
            "comment_content",
        ]
        for field in required_fields:
            if not review.get(field):
                errors.append(f"Missing required field: {field}")

        if self.config.validate_ratings and "rating" in review:
            try:
                rating = int(review["rating"])
                if not 1 <= rating <= 5:
                    errors.append("Rating must be between 1 and 5")
            except (ValueError, TypeError):
                errors.append("Invalid rating format")

        return len(errors) == 0, errors

    def convert_item(self, review: Any) -> Optional[Dict[str, Any]]:
        product_id = str(review["comment_post_ID"])
        product_handle = self.product_mapping.get(
            product_id, self.create_handle(product_id)
        )

        if product_id not in self.product_mapping:
            self.stats["reviews_with_missing_product"] += 1

        try:
            rating = int(review.get("rating", self.config.default_rating))
            rating = max(1, min(5, rating))
        except (ValueError, TypeError):
            rating = self.config.default_rating

        return {
            "Product Handle": product_handle,
            "Review Date": self.format_date(str(review.get("comment_date", ""))),
            "Reviewer Name": self.clean_text(review["comment_author"]),
            "Reviewer Email": self.clean_text(
                review.get("comment_author_email", "")
            ),
            "Review Title": self.clean_text(review.get("title", "")),
            "Rating": rating,
            "Review Text": self.clean_html(str(review["comment_content"])),
            "Review Status": "published"
            if str(review.get("comment_approved", "1")) == "1"
            else "unpublished",
            "Reviewer Location": self.clean_text(
                review.get("comment_author_location", "")
            ),
            "Verified Buyer": str(review.get("verified", "0")) == "1",
        }

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, str]:
        """Load product ID to handle mapping."""
        if "woo_id" in mapping_df.columns and "shopify_handle" in mapping_df.columns:
            return dict(
                zip(
                    mapping_df["woo_id"].astype(str),
                    mapping_df["shopify_handle"].astype(str),
                )
            )
        return {}

    def convert_reviews(
        self,
        input_file: str,
        output_file: str,
        product_mapping_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        """Convert WooCommerce reviews to Shopify format."""
        if product_mapping_file and Path(product_mapping_file).exists():
            mapping_df = pd.read_csv(
                product_mapping_file, encoding=self.config.encoding
            )
            self.product_mapping = self.load_mapping(mapping_df)
            self.logger.info(
                f"Loaded {len(self.product_mapping)} product mappings"
            )

        self.convert_data(input_file, output_file, dry_run=dry_run)
