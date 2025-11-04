# base_migration.py
from abc import ABC, abstractmethod
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple
import json

class BaseMigrationTool(ABC):
    """Base class for WooCommerce to Shopify migration tools."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize migration tool with configuration.
        
        Args:
            config (dict, optional): Configuration dictionary
        """
        self.config = config or {}
        self.stats = {
            'total_items': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0,
            'details': {}  # For tool-specific statistics
        }
        self.setup_logging()

    def setup_logging(self) -> None:
        """Configure logging system."""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Use tool-specific name in log file
        tool_name = self.__class__.__name__.lower()
        log_file = log_dir / f'{tool_name}_{datetime.now():%Y%m%d_%H%M%S}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def generate_report(self, output_file: str) -> None:
        """
        Generate migration report.
        
        Args:
            output_file (str): Path to the output file
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'tool_name': self.__class__.__name__,
            'input_file': self.config.get('input_file', 'N/A'),
            'output_file': output_file,
            'statistics': self.stats,
            'success_rate': f"{(self.stats['successful'] / max(self.stats['total_items'], 1) * 100):.2f}%",
            'configuration': self.config
        }
        
        # Save report
        report_file = Path('reports') / f'{self.__class__.__name__.lower()}_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Migration report saved to {report_file}")

    @abstractmethod
    def validate_item(self, item: Dict) -> Tuple[bool, List[str]]:
        """
        Validate an item before conversion.
        
        Args:
            item (dict): Item data to validate
            
        Returns:
            tuple: (is_valid, list of error messages)
        """
        pass

    @abstractmethod
    def convert_item(self, item: Dict) -> Optional[Dict]:
        """
        Convert a single item to Shopify format.
        
        Args:
            item (dict): Item data to convert
            
        Returns:
            dict: Converted item data for Shopify
        """
        pass

    def convert_data(self, input_file: str, output_file: str, mapping_file: Optional[str] = None) -> None:
        """
        Convert WooCommerce data to Shopify format.
        
        Args:
            input_file (str): Path to WooCommerce export CSV
            output_file (str): Path to save Shopify import CSV
            mapping_file (str, optional): Path to ID mapping file
        """
        try:
            self.logger.info(f"Starting migration from {input_file}")
            
            # Load mapping if provided
            mapping = {}
            if mapping_file:
                mapping_df = pd.read_csv(mapping_file)
                mapping = self.load_mapping(mapping_df)
            
            # Read WooCommerce export
            df = pd.read_csv(input_file)
            self.stats['total_items'] = len(df)
            
            converted_items = []
            
            for _, item in df.iterrows():
                try:
                    # Validate item
                    is_valid, errors = self.validate_item(item)
                    if not is_valid:
                        self.logger.warning(f"Invalid item {item.get('id', 'unknown')}: {', '.join(errors)}")
                        self.stats['warnings'] += 1
                        continue
                    
                    # Convert item
                    converted = self.convert_item(item)
                    if converted:
                        converted_items.append(converted)
                        self.stats['successful'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing item {item.get('id', 'unknown')}: {str(e)}")
                    self.stats['failed'] += 1
            
            # Save to CSV
            if converted_items:
                output_df = pd.DataFrame(converted_items)
                output_df.to_csv(output_file, index=False)
                
                # Generate report
                self.generate_report(output_file)
                
                self.logger.info(f"Migration completed. See {output_file} for results.")
            else:
                self.logger.warning("No items were successfully processed!")
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            raise

    @abstractmethod
    def load_mapping(self, mapping_df: pd.DataFrame) -> Dict:
        """
        Load and process mapping data.
        
        Args:
            mapping_df (DataFrame): Mapping data
            
        Returns:
            dict: Processed mapping dictionary
        """
        pass

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        return str(text).strip()

    @staticmethod
    def create_handle(text: str) -> str:
        """
        Create URL-friendly handle from text.
        
        Args:
            text (str): Text to convert to handle
            
        Returns:
            str: URL-friendly handle
        """
        import re
        handle = text.lower()
        handle = re.sub(r'[^a-z0-9]+', '-', handle)
        return handle.strip('-')