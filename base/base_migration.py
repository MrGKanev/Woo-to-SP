# base/base_migration.py
"""Base migration module providing common functionality for all migration tools."""

from abc import ABC, abstractmethod
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any, Iterator, Generator
import json
import re
from tqdm import tqdm


class BaseMigrationTool(ABC):
    """
    Abstract base class for WooCommerce to Shopify migration tools.

    Provides common functionality:
    - Logging setup
    - Statistics tracking
    - Report generation
    - Batch processing
    - Progress bar support
    - Common utility methods
    """

    # Override in subclasses for tool-specific naming
    TOOL_NAME: str = "migration"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize migration tool with configuration.

        Args:
            config: Configuration dictionary with tool-specific options
        """
        self.config = self._get_default_config()
        if config:
            self.config.update(config)

        self.stats = self._init_stats()
        self.setup_logging()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration. Override in subclasses for tool-specific defaults.

        Returns:
            Dictionary with default configuration values
        """
        return {
            'batch_size': 100,
            'show_progress': True,
        }

    def _init_stats(self) -> Dict[str, Any]:
        """
        Initialize statistics dictionary. Override in subclasses for additional stats.

        Returns:
            Dictionary with statistics counters
        """
        return {
            'total_items': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'start_time': None,
            'end_time': None,
        }

    def setup_logging(self) -> None:
        """Configure logging system with file and console output."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        tool_name = self.TOOL_NAME.lower().replace(' ', '_')
        log_file = log_dir / f'{tool_name}_{datetime.now():%Y%m%d_%H%M%S}.log'

        # Create a new logger for this instance
        self.logger = logging.getLogger(f'{self.__class__.__name__}_{id(self)}')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        self.logger.addHandler(console_handler)

    def generate_report(self, output_file: str) -> None:
        """
        Generate migration report in JSON format.

        Args:
            output_file: Path to the output file
        """
        # Calculate duration if times are set
        duration = None
        if self.stats.get('start_time') and self.stats.get('end_time'):
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        total = max(self.stats.get('total_items', 0), 1)

        report = {
            'timestamp': datetime.now().isoformat(),
            'tool_name': self.__class__.__name__,
            'input_file': self.config.get('input_file', 'N/A'),
            'output_file': output_file,
            'statistics': {k: v for k, v in self.stats.items()
                         if k not in ('start_time', 'end_time')},
            'success_rate': f"{(self.stats['successful'] / total * 100):.2f}%",
            'duration_seconds': duration,
            'configuration': {k: v for k, v in self.config.items()
                            if not callable(v)}
        }

        # Save report
        report_dir = Path('reports')
        report_dir.mkdir(exist_ok=True)

        tool_name = self.TOOL_NAME.lower().replace(' ', '_')
        report_file = report_dir / f'{tool_name}_report_{datetime.now():%Y%m%d_%H%M%S}.json'

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Migration report saved to {report_file}")

    def iter_batches(
        self,
        df: pd.DataFrame,
        desc: str = "Processing"
    ) -> Generator[Tuple[int, pd.Series], None, None]:
        """
        Iterate over dataframe rows with optional progress bar.

        Args:
            df: DataFrame to iterate over
            desc: Description for progress bar

        Yields:
            Tuple of (index, row) for each row
        """
        iterator = df.iterrows()

        if self.config.get('show_progress', True):
            iterator = tqdm(
                iterator,
                total=len(df),
                desc=desc,
                unit="items"
            )

        for idx, row in iterator:
            yield idx, row

    def process_in_batches(
        self,
        items: List[Any],
        process_func: callable,
        desc: str = "Processing"
    ) -> List[Any]:
        """
        Process items in batches with progress tracking.

        Args:
            items: List of items to process
            process_func: Function to apply to each item
            desc: Description for progress bar

        Returns:
            List of processed results
        """
        batch_size = self.config.get('batch_size', 100)
        results = []

        iterator = range(0, len(items), batch_size)
        if self.config.get('show_progress', True):
            iterator = tqdm(
                iterator,
                total=len(items) // batch_size + 1,
                desc=f"{desc} (batches)",
                unit="batch"
            )

        for i in iterator:
            batch = items[i:i + batch_size]
            for item in batch:
                try:
                    result = process_func(item)
                    if result is not None:
                        results.append(result)
                        self.stats['successful'] += 1
                except Exception as e:
                    self.logger.error(f"Error processing item: {str(e)}")
                    self.stats['failed'] += 1

        return results

    @abstractmethod
    def validate_item(self, item: Any) -> Tuple[bool, List[str]]:
        """
        Validate an item before conversion.

        Args:
            item: Item data to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        pass

    @abstractmethod
    def convert_item(self, item: Any) -> Optional[Dict[str, Any]]:
        """
        Convert a single item to Shopify format.

        Args:
            item: Item data to convert

        Returns:
            Converted item data for Shopify, or None if conversion failed
        """
        pass

    def convert_data(
        self,
        input_file: str,
        output_file: str,
        mapping_file: Optional[str] = None
    ) -> None:
        """
        Main conversion method - converts WooCommerce data to Shopify format.

        Args:
            input_file: Path to WooCommerce export CSV
            output_file: Path to save Shopify import CSV
            mapping_file: Optional path to ID mapping file
        """
        try:
            self.stats['start_time'] = datetime.now()
            self.config['input_file'] = input_file

            self.logger.info(f"Starting {self.TOOL_NAME} migration from {input_file}")

            # Load mapping if provided
            mapping = {}
            if mapping_file and Path(mapping_file).exists():
                mapping_df = pd.read_csv(mapping_file)
                mapping = self.load_mapping(mapping_df)
                self.logger.info(f"Loaded {len(mapping)} mappings from {mapping_file}")

            # Read input data
            df = pd.read_csv(input_file)
            self.stats['total_items'] = len(df)
            self.logger.info(f"Found {len(df)} items to process")

            converted_items = []

            for _, item in self.iter_batches(df, desc=f"Converting {self.TOOL_NAME}"):
                try:
                    # Validate item
                    is_valid, errors = self.validate_item(item)
                    if not is_valid:
                        item_id = item.get('id', item.get('ID', 'unknown'))
                        self.logger.warning(f"Invalid item {item_id}: {', '.join(errors)}")
                        self.stats['warnings'] += 1
                        continue

                    # Convert item
                    converted = self.convert_item(item)
                    if converted:
                        if isinstance(converted, list):
                            converted_items.extend(converted)
                        else:
                            converted_items.append(converted)
                        self.stats['successful'] += 1

                except Exception as e:
                    item_id = item.get('id', item.get('ID', 'unknown'))
                    self.logger.error(f"Error processing item {item_id}: {str(e)}")
                    self.stats['failed'] += 1

            # Save to CSV
            if converted_items:
                output_df = pd.DataFrame(converted_items)
                output_df.to_csv(output_file, index=False)
                self.logger.info(f"Saved {len(converted_items)} items to {output_file}")
            else:
                self.logger.warning("No items were successfully processed!")

            self.stats['end_time'] = datetime.now()

            # Generate report
            self.generate_report(output_file)

            self.logger.info(f"{self.TOOL_NAME} migration completed.")
            self._log_summary()

        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

    def _log_summary(self) -> None:
        """Log migration summary statistics."""
        self.logger.info("=" * 50)
        self.logger.info("Migration Summary:")
        self.logger.info(f"  Total items: {self.stats['total_items']}")
        self.logger.info(f"  Successful: {self.stats['successful']}")
        self.logger.info(f"  Failed: {self.stats['failed']}")
        self.logger.info(f"  Warnings: {self.stats['warnings']}")

        if self.stats.get('start_time') and self.stats.get('end_time'):
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            self.logger.info(f"  Duration: {duration:.2f} seconds")
        self.logger.info("=" * 50)

    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Load and process mapping data. Override for custom mapping logic.

        Args:
            mapping_df: DataFrame with mapping data

        Returns:
            Dictionary with processed mapping
        """
        # Default implementation - assumes 'source_id' and 'target_id' columns
        if 'source_id' in mapping_df.columns and 'target_id' in mapping_df.columns:
            return dict(zip(mapping_df['source_id'], mapping_df['target_id']))
        return {}

    # Utility methods available to all subclasses

    @staticmethod
    def clean_text(text: Any) -> str:
        """
        Clean and normalize text content.

        Args:
            text: Text to clean

        Returns:
            Cleaned text string
        """
        if pd.isna(text) or text is None:
            return ""
        return str(text).strip()

    @staticmethod
    def create_handle(text: str) -> str:
        """
        Create URL-friendly handle from text.

        Args:
            text: Text to convert to handle

        Returns:
            URL-friendly handle string
        """
        if not text:
            return ""
        handle = str(text).lower()
        handle = re.sub(r'[^a-z0-9]+', '-', handle)
        return handle.strip('-')

    @staticmethod
    def clean_phone(phone: Any) -> str:
        """
        Clean phone numbers to international format.

        Args:
            phone: Phone number to clean

        Returns:
            Cleaned phone number string
        """
        if pd.isna(phone) or not phone:
            return ''
        phone = re.sub(r'[^\d+]', '', str(phone))
        if not phone.startswith('+'):
            if len(phone) == 10:
                phone = '+1' + phone
        return phone

    @staticmethod
    def clean_html(html_content: str) -> str:
        """
        Clean HTML content while preserving basic structure.

        Args:
            html_content: HTML string to clean

        Returns:
            Cleaned HTML string
        """
        if not html_content:
            return ""

        # Convert common HTML entities
        html_content = html_content.replace('&nbsp;', ' ')
        html_content = html_content.replace('&amp;', '&')
        html_content = html_content.replace('&quot;', '"')

        # Remove script and style elements
        html_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<style.*?</style>', '', html_content, flags=re.DOTALL)

        # Remove WordPress shortcodes
        html_content = re.sub(r'\[[^\]]+\]', '', html_content)

        # Preserve line breaks
        html_content = html_content.replace('</p>', '</p>\n')
        html_content = html_content.replace('<br', '\n<br')

        # Remove remaining HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)

        # Clean up whitespace
        html_content = re.sub(r'\s+', ' ', html_content)

        return html_content.strip()

    @staticmethod
    def format_date(date_str: str, output_format: str = '%Y-%m-%d %H:%M:%S') -> str:
        """
        Format date string to standard format.

        Args:
            date_str: Date string to format
            output_format: Desired output format

        Returns:
            Formatted date string or empty string on failure
        """
        if not date_str:
            return ""

        input_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
        ]

        for fmt in input_formats:
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                return dt.strftime(output_format)
            except ValueError:
                continue

        return ""

    def parse_json_field(self, field: Any, default: Any = None) -> Any:
        """
        Safely parse a JSON field that might be string or already parsed.

        Args:
            field: Field value to parse
            default: Default value if parsing fails

        Returns:
            Parsed value or default
        """
        if pd.isna(field) or field is None:
            return default if default is not None else {}

        if isinstance(field, (dict, list)):
            return field

        if isinstance(field, str):
            try:
                return json.loads(field)
            except json.JSONDecodeError:
                self.logger.debug(f"Could not parse JSON: {field[:50]}...")
                return default if default is not None else {}

        return default if default is not None else {}
