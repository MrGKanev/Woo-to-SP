# WP to SP Discount Code Migration Tool

A Python tool for migrating WordPress/WooCommerce coupons to Shopify discount codes with support for various discount types, product restrictions, and usage limits.

## 🌟 Features

- ✨ Converts discount codes
- 💰 Handles percentage and fixed amount discounts
- 📅 Preserves expiry dates
- 🛍️ Product-specific restrictions
- 🔄 Usage limit tracking
- 📊 Detailed migration reports
- 🧹 Code cleaning and validation
- 🚨 Error handling
- 💾 Batch processing

## 📋 Prerequisites

- Python 3.8+
- WordPress/WooCommerce coupon export in CSV format
- Product mapping file (optional)

## ⚙️ Configuration

```python
config = {
    'default_minimum_amount': 0,
    'default_usage_limit': None,
    'batch_size': 500
}
```

## 📝 Input Format

### Coupons Export (wp_coupons_export.csv)

```csv
code,discount_type,amount,minimum_amount,product_ids,exclude_product_ids,date_created,date_expires,usage_limit,individual_use,enabled
SUMMER20,percent,20,50,1234;5678,,2024-01-01,2024-12-31,100,yes,yes
```

### Product Mapping (Optional - product_mapping.csv)

```csv
woo_id,shopify_id
1234,987654321
5678,987654322
```

## 💻 Usage

### Basic Usage

```python
from src.wp_sp_discounts import DiscountMigrationTool

tool = DiscountMigrationTool()
tool.convert_discounts(
    input_file="data/input/wp_coupons_export.csv",
    output_file="data/output/sp_discounts_import.csv"
)
```

### Advanced Usage

```python
config = {
    'default_minimum_amount': 10,
    'default_usage_limit': 1000,
    'batch_size': 1000
}

tool = DiscountMigrationTool(config)
tool.convert_discounts(
    input_file="data/input/wp_coupons_export.csv",
    output_file="data/output/sp_discounts_import.csv",
    product_mapping_file="data/input/product_mapping.csv"
)
```

## 📤 Output Format

```csv
Discount Code,Type,Amount,Minimum Purchase Amount,Starts At,Ends At,Usage Limit,Once Per Customer,Status,Applies To,Products,Excluded Products
SUMMER20,percentage,20,50,2024-01-01 00:00:00,2024-12-31 23:59:59,100,true,enabled,specific,987654321;987654322,
```

## 📊 Reports

Generated report example:

```json
{
  "timestamp": "2024-01-15T14:30:00",
  "statistics": {
    "total_coupons": 100,
    "successful": 98,
    "failed": 1,
    "warnings": 1
  },
  "success_rate": "98.00%"
}
```

## ⚠️ Error Handling

The tool handles:

- Invalid discount codes
- Missing required fields
- Invalid dates
- Product mapping issues
- Malformed data

## 🔄 Supported Discount Types

- Percentage discounts
- Fixed amount discounts
- Cart discounts
- Product-specific discounts

## 🚫 Limitations

- Cannot migrate complex rule-based discounts
- Usage history is imported as count only
- Customer-specific restrictions need manual setup
- Some advanced WooCommerce features not supported in Shopify

## ✅ Best Practices

1. Backup your discount codes before migration
2. Test with a small batch first
3. Verify discount calculations
4. Check product restrictions
5. Review usage limits
6. Monitor expiry dates
7. Validate converted codes in Shopify

## 🔍 Troubleshooting

Common issues and solutions:

### Invalid Discount Code

```
Warning: Invalid coupon code format
```

Solution: Codes are automatically cleaned and formatted

### Product Mapping

```
Warning: Product ID not found in mapping
```

Solution: Update product mapping file with missing products

### Date Format

```
Warning: Invalid date format
```

Solution: Ensure dates are in YYYY-MM-DD format
