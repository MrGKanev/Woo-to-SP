# WooCommerce to Shopify - Customer Migration Tool

Convert WooCommerce customers and MailChimp subscribers to Shopify customer format.

## Features

- 👥 WooCommerce customer migration
- 📧 MailChimp subscriber integration
- 🌎 International address formatting
- 📱 Phone number standardization
- 🎯 Marketing preference preservation
- 🔄 Duplicate handling
- 📊 Detailed reporting

## Usage

1. **Basic Usage**

```bash
python main.py \
  --woo-file customers_export.csv \
  --mailchimp-folder info \
  --output shopify_customers.csv
```

2. **Configuration Example**

```python
tool = CustomerMigrationTool()
tool.convert_customers(
    woo_file="woocommerce_customers.csv",
    mailchimp_folder="mailchimp_export",  # or "mailchimp_export.zip"
    output_file="shopify_customers.csv"
)
```

## Input Requirements

### WooCommerce Export

- Email
- First Name
- Last Name
- Billing Address
- Shipping Address
- Accepts Marketing
- Total Spent
- Order Count

### MailChimp Export Structure

```
mailchimp_export/
├── lists/
│   └── [list-id]/
│       ├── members/
│       │   └── members.csv
│       ├── merge-fields.csv
│       └── segments.csv
```

## Output Format

Generates Shopify-compatible CSV with:

- Email
- First Name
- Last Name
- Company
- Address Details
- Phone
- Marketing Preferences
- Tags
- Customer Type

## Data Mapping

### WooCommerce to Shopify

- Email → Email
- First Name → First Name
- Last Name → Last Name
- Billing Address → Default Address
- Shipping Address → Additional Address
- Accepts Marketing → Accepts Marketing

### MailChimp to Shopify

- Email Address → Email
- MERGE1 → First Name
- MERGE2 → Last Name
- Status → Tags
- List Name → Tags

## Best Practices

1. 🔄 Export fresh data from both sources
2. ✅ Test with a small dataset first
3. 📋 Verify customer counts match
4. 🔍 Check for duplicate handling
5. 💾 Keep original exports as backup

## Limitations

- Cannot migrate password data
- Limited to 3 address fields per customer
- Some custom fields need manual mapping
- Campaign history not transferred
- Automation data not included

## Support

See main project README for general help. For customer-specific issues:

1. Check logs/customer_migration_[timestamp].log
2. Review reports/customer_migration_report_[timestamp].json
3. Verify export formats match requirements
