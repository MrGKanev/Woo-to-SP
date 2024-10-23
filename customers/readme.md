# WooCommerce/MailChimp to Shopify Customer Migration Tool 

A Python script to convert WooCommerce customers and MailChimp subscribers to Shopify customer format.

## Features

- Processes both WooCommerce customers and MailChimp subscribers
- Deduplicates customers by email
- Handles MailChimp merge fields
- Preserves customer segments and tags
- Supports multiple MailChimp lists
- Processes ZIP or folder exports
- Maintains subscription status
- Handles international phone numbers

## Installation

1. Ensure you're in the customers directory:

```bash
cd customers
```

2. Install required dependencies:

```bash
pip install pandas
```

## Usage

### Basic Usage

```python
from woo_to_shopify_customers import CustomerMigrationTool

tool = CustomerMigrationTool()
tool.convert_customers(
    woo_file="woocommerce_customers.csv",
    mailchimp_folder="mailchimp_export",  # or "mailchimp_export.zip"
    output_file="shopify_customers.csv"
)
```

### MailChimp Export Structure

The script expects the MailChimp export folder to contain:

```
mailchimp_export/
├── lists/
│   └── [list-id]/
│       ├── members/
│       │   └── members.csv
│       ├── merge-fields.csv
│       └── segments.csv
```

## Data Sources

### WooCommerce Customer Export

Required fields:

- Email
- First Name
- Last Name
- Billing Address
- Shipping Address
- Accepts Marketing
- Total Spent
- Order Count

### MailChimp Export

The tool processes:

1. Subscriber information from members.csv
2. Custom fields from merge-fields.csv
3. Segments/tags from segments.csv

## Data Mapping

### WooCommerce to Shopify

| WooCommerce Field | Shopify Field |
|-------------------|---------------|
| Email | Email |
| First Name | First Name |
| Last Name | Last Name |
| Billing Address | Default Address |
| Shipping Address | Additional Address |
| Accepts Marketing | Accepts Marketing |

### MailChimp to Shopify

| MailChimp Field | Shopify Field |
|-----------------|---------------|
| Email Address | Email |
| MERGE1 | First Name |
| MERGE2 | Last Name |
| Status | Tags |
| List Name | Tags |

## Error Handling

The script handles:

- Missing files or folders
- Malformed CSV files
- Invalid JSON data
- Missing fields
- Duplicate customers
- ZIP file processing errors

## Limitations

- Cannot migrate password data
- Limited to 3 address fields per customer
- Some custom fields may need manual mapping
- Campaign history not transferred
- Automation data not included

## Best Practices

1. Export fresh data from both sources
2. Test with a small dataset first
3. Verify customer counts match
4. Check for duplicate handling
5. Keep original exports as backup

## Troubleshooting

Common issues:

1. **MailChimp Folder Structure:**

   ```
   Error loading MailChimp info folder
   ```

   - Verify folder structure matches expected format
   - Check file permissions

2. **Merge Fields:**

   ```
   KeyError: 'MERGE1'
   ```

   - Check merge-fields.csv exists
   - Verify merge field mapping

3. **Memory Issues:**

   ```
   MemoryError
   ```

   - Process data in smaller batches
   - Increase available RAM
