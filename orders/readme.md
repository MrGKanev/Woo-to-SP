# WooCommerce to Shopify - Order Migration Tool

Convert WooCommerce orders to Shopify format, including line items, meta fields, and customer information.

## Features

- 🛍️ Complete order history transfer
- 📦 Line item preservation
- 💰 Tax and shipping details
- 🏷️ Custom meta field mapping
- 📝 Order notes migration
- 🔄 Status mapping
- 📊 Detailed reporting

## Usage

1. **Basic Usage**

```bash
python main.py \
  --input woocommerce_orders_export.csv \
  --output shopify_orders_import.csv \
  --meta-mapping meta_mapping.csv
```

2. **Meta Mapping Configuration**

```csv
meta_key,name_prefix,name_suffix,sku_prefix,price_field
Accent Piece,,Accent Piece,accent-piece-,accent_piece
Burr Set,,,burr-set-,burr_set
Optional Add-ons,,,addon-,addon
```

## Input Requirements

### Orders Export

Required fields:

- Order Number
- Customer Email
- Status
- Currency
- Line Items
- Meta Data
- Addresses
- Tax/Shipping

### Meta Mapping File Format

| Column | Description | Example |
|--------|-------------|---------|
| meta_key | WooCommerce meta field name | "Accent Piece" |
| name_prefix | Text before value (optional) | "Custom" |
| name_suffix | Text after value (optional) | "Accent Piece" |
| sku_prefix | SKU generation prefix | "accent-piece-" |
| price_field | Price lookup field | "accent_piece" |

## Output Format

Generates Shopify-compatible CSV with:

- Order details
- Line items
- Customer information
- Shipping/billing addresses
- Tax information
- Meta item conversions

## Best Practices

1. ✅ Always backup order data
2. 🔄 Test with small batch
3. 📋 Verify meta mapping
4. 💾 Keep original exports
5. 📊 Monitor migration logs

## Limitations

- No password migration
- Limited to 3 address fields
- Some custom fields need mapping
- Notes require configuration
- No refund history transfer

## Support

See main project README for general help. For order-specific issues:

1. Check logs/order_migration_[timestamp].log
2. Review reports/order_migration_report_[timestamp].json
3. Verify meta mapping configuration
