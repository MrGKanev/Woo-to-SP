"""Pydantic configuration models for all migration tools."""

from typing import Optional

from pydantic import BaseModel, Field


class MigrationConfig(BaseModel):
    """Base configuration shared by all migration tools."""

    batch_size: int = Field(default=100, ge=1)
    encoding: str = "utf-8"
    show_progress: bool = True

    model_config = {"extra": "forbid"}


class ProductConfig(MigrationConfig):
    """Configuration for product migration."""

    image_migration: bool = True
    inventory_tracking: bool = True
    default_weight_unit: str = "kg"
    skip_drafts: bool = False


class CustomerConfig(MigrationConfig):
    """Configuration for customer migration."""

    pass


class OrderConfig(MigrationConfig):
    """Configuration for order migration."""

    max_line_items: int = Field(default=20, ge=1)
    default_currency: str = "USD"


class CollectionConfig(MigrationConfig):
    """Configuration for collection/category migration."""

    use_smart_collections: bool = True
    default_sort_order: str = "best-selling"


class ReviewConfig(MigrationConfig):
    """Configuration for review migration."""

    validate_ratings: bool = True
    default_rating: int = Field(default=5, ge=1, le=5)


class DiscountConfig(MigrationConfig):
    """Configuration for discount/coupon migration."""

    default_minimum_amount: float = Field(default=0, ge=0)
    default_usage_limit: Optional[int] = None
    max_code_length: int = Field(default=50, ge=1)
