"""Base migration module providing common functionality for all migration tools."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

import pandas as pd
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

from woo_to_sp.config import MigrationConfig
from woo_to_sp.utils import (
    clean_html,
    clean_phone,
    clean_text,
    create_handle,
    format_date,
    parse_json_field,
)


class BaseMigrationTool(ABC):
    """
    Abstract base class for WooCommerce to Shopify migration tools.

    Provides common functionality:
    - Logging setup
    - Statistics tracking
    - Report generation
    - Batch processing
    - Progress bar support (Rich)
    - Common utility methods
    """

    TOOL_NAME: str = "migration"
    REQUIRED_COLUMNS: List[str] = []

    def __init__(self, config: Optional[MigrationConfig] = None):
        self.config = config or self._get_default_config()
        self.stats = self._init_stats()
        self.errors: List[Dict[str, Any]] = []
        self.setup_logging()

    def _get_default_config(self) -> MigrationConfig:
        """Get default configuration. Override in subclasses for tool-specific defaults."""
        return MigrationConfig()

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize statistics dictionary. Override in subclasses for additional stats."""
        return {
            "total_items": 0,
            "successful": 0,
            "failed": 0,
            "warnings": 0,
            "start_time": None,
            "end_time": None,
        }

    def setup_logging(self) -> None:
        """Configure logging system with file and console output."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        tool_name = self.TOOL_NAME.lower().replace(" ", "_")
        log_file = log_dir / f"{tool_name}_{datetime.now():%Y%m%d_%H%M%S}.log"

        self.logger = logging.getLogger(f"{self.__class__.__name__}_{id(self)}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self.logger.addHandler(console_handler)

    def validate_columns(self, df: pd.DataFrame) -> None:
        """Validate that required columns exist in the DataFrame."""
        if not self.REQUIRED_COLUMNS:
            return
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

    def generate_report(self, output_file: str) -> None:
        """Generate migration report in JSON format."""
        duration = None
        if self.stats.get("start_time") and self.stats.get("end_time"):
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        total = max(self.stats.get("total_items", 0), 1)

        report = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": self.__class__.__name__,
            "input_file": getattr(self, "_input_file", "N/A"),
            "output_file": output_file,
            "statistics": {
                k: v for k, v in self.stats.items() if k not in ("start_time", "end_time")
            },
            "success_rate": f"{(self.stats['successful'] / total * 100):.2f}%",
            "duration_seconds": duration,
            "errors": self.errors[-50:],
        }

        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)

        tool_name = self.TOOL_NAME.lower().replace(" ", "_")
        report_file = report_dir / f"{tool_name}_report_{datetime.now():%Y%m%d_%H%M%S}.json"

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Migration report saved to {report_file}")

    def iter_batches(
        self,
        df: pd.DataFrame,
        desc: str = "Processing",
    ) -> Generator[Tuple[int, pd.Series], None, None]:
        """Iterate over dataframe rows with optional Rich progress bar."""
        if self.config.show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
            ) as progress:
                task = progress.add_task(desc, total=len(df))
                for idx, row in df.iterrows():
                    yield idx, row
                    progress.advance(task)
        else:
            for idx, row in df.iterrows():
                yield idx, row

    @abstractmethod
    def validate_item(self, item: Any) -> Tuple[bool, List[str]]:
        """Validate an item before conversion."""
        pass

    @abstractmethod
    def convert_item(self, item: Any) -> Any:
        """Convert a single item to Shopify format."""
        pass

    def convert_data(
        self,
        input_file: str,
        output_file: str,
        mapping_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        """Main conversion method - converts WooCommerce data to Shopify format."""
        try:
            self.stats["start_time"] = datetime.now()
            self._input_file = input_file

            self.logger.info(f"Starting {self.TOOL_NAME} migration from {input_file}")

            mapping = {}
            if mapping_file and Path(mapping_file).exists():
                mapping_df = pd.read_csv(mapping_file, encoding=self.config.encoding)
                mapping = self.load_mapping(mapping_df)
                self.logger.info(f"Loaded {len(mapping)} mappings from {mapping_file}")

            df = pd.read_csv(input_file, encoding=self.config.encoding)
            self.validate_columns(df)
            self.stats["total_items"] = len(df)
            self.logger.info(f"Found {len(df)} items to process")

            converted_items = []

            for _, item in self.iter_batches(df, desc=f"Converting {self.TOOL_NAME}"):
                try:
                    is_valid, errors = self.validate_item(item)
                    if not is_valid:
                        item_id = item.get("id", item.get("ID", "unknown"))
                        self.logger.warning(f"Invalid item {item_id}: {', '.join(errors)}")
                        self.stats["warnings"] += 1
                        continue

                    converted = self.convert_item(item)
                    if converted:
                        if isinstance(converted, list):
                            converted_items.extend(converted)
                        else:
                            converted_items.append(converted)
                        self.stats["successful"] += 1

                except Exception as e:
                    item_id = item.get("id", item.get("ID", "unknown"))
                    error_detail = {
                        "item_id": str(item_id),
                        "error": str(e),
                        "type": type(e).__name__,
                    }
                    self.errors.append(error_detail)
                    self.logger.error(f"Error processing item {item_id}: {e}")
                    self.stats["failed"] += 1

            if dry_run:
                self.logger.info(
                    f"Dry run complete: {len(converted_items)} items would be written"
                )
            elif converted_items:
                output_df = pd.DataFrame(converted_items)
                output_df.to_csv(output_file, index=False, encoding=self.config.encoding)
                self.logger.info(f"Saved {len(converted_items)} items to {output_file}")
            else:
                self.logger.warning("No items were successfully processed!")

            self.stats["end_time"] = datetime.now()
            self.generate_report(output_file)

            self.logger.info(f"{self.TOOL_NAME} migration completed.")

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            raise

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, Any]:
        """Load and process mapping data. Override for custom mapping logic."""
        if "source_id" in mapping_df.columns and "target_id" in mapping_df.columns:
            return dict(zip(mapping_df["source_id"], mapping_df["target_id"]))
        return {}

    # Delegate utility methods to standalone functions for backward compatibility

    @staticmethod
    def clean_text(text: Any) -> str:
        return clean_text(text)

    @staticmethod
    def create_handle(text: str) -> str:
        return create_handle(text)

    @staticmethod
    def clean_phone(phone: Any) -> str:
        return clean_phone(phone)

    @staticmethod
    def clean_html(html_content: str) -> str:
        return clean_html(html_content)

    @staticmethod
    def format_date(date_str: str, output_format: str = "%Y-%m-%d %H:%M:%S") -> str:
        return format_date(date_str, output_format)

    def parse_json_field(self, field: Any, default: Any = None) -> Any:
        return parse_json_field(field, default)
