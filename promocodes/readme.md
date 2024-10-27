# WooCommerce to Shopify - Promo-codes/Discounts Migration Tool

Convert WooCommerce coupons to Shopify discount codes.

## Features

- 🏷️ Coupon code conversion
- 💰 Multiple discount types
- 📅 Date range preservation
- 🛍️ Product restrictions
- 🔢 Usage limit tracking
- 👤 Customer specific rules
- 📊 Detailed reporting

## Usage

1. **Basic Usage**

```bash
python main.py \
  --input wp_coupons_export.csv \
  --output sp_discounts_import.csv \
  --product-mapping product_mapping.csv
```

2. **Configuration Example**

```python
config = {
    'default_minimum_amount': 0,
    'default_usage_limit': None,
    'batch_size': 500
}
```

## Input Format

### Coupons Export

```csv
code,discount_type,amount,minimum_amount,product_ids,exclude_product_ids,date_created,date_expires,usage_limit
SUMMER20,percent,20,50,1234;5678,,2024-01-01,2024-12-31,100
```

### Product Mapping (Optional)

```csv
woo_id,shopify_id
1234,987654321
5678,987654322
```

## Output Format

Generates Shopify-compatible CSV with:

- Discount Code
- Type
- Amount
- Minimum Purchase Amount
- Date Range
- Usage Limits
- Product Restrictions
- Status

## Supported Discount Types

- Percentage discounts
- Fixed amount discounts
- Cart discounts
- Product-specific discounts

## Best Practices

1. 💾 Backup discount codes
2. ✅ Test with small batch
3. 📋 Verify calculations
4. 🔍 Check restrictions
5. 📊 Monitor logs

## Limitations

- No complex rule migration
- Usage history as count only
- Customer restrictions need setup
- Some WooCommerce features unsupported

## Support

See main project README for general help. For discount-specific issues:

1. Check logs/discount_migration_[timestamp].log
2. Review reports/discount_migration_report_[timestamp].json
3. Verify coupon export format
