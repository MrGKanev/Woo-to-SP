# WooCommerce to Shopify Order Migration Tool

A Python script to convert WooCommerce order exports to Shopify-compatible format.

## Features

- Converts basic order information
- Handles customer details
- Processes billing and shipping addresses
- Converts order statuses
- Maintains line items (products)
- Preserves tax and shipping information
- Handles product variations
- Supports international phone numbers
- Processes dates correctly
- Converts meta fields to separate line items (e.g., add-ons, customizations)

## Installation

1. Ensure you're in the orders directory:

```bash
cd orders
```

2. Install required dependencies:

```bash
pip install pandas
```

## Usage

1. Export your WooCommerce orders:
   - Install "Order Import Export for WooCommerce" plugin
   - Go to WooCommerce > Export/Import Orders
   - Export your orders as CSV

2. Create a meta mapping file (meta_mapping.csv):

```csv
meta_key,name_prefix,name_suffix,sku_prefix,price_field
Accent Piece,,Accent Piece,accent-piece-,accent_piece
Burr Set,,,burr-set-,burr_set
Optional Add-ons,,,addon-,addon
```

3. Run the conversion script:

```python
python orders.py
```

You can modify the input/output file paths in the script:

```python
input_file = "woocommerce_orders_export.csv"     # Your WooCommerce export
output_file = "shopify_orders_import.csv"        # Where to save Shopify import
meta_mapping_file = "meta_mapping.csv"           # Meta field mapping configuration
```

## Meta Mapping Configuration

The script uses a CSV file to configure how meta fields are converted to separate line items.

### Meta Mapping CSV Format

| Column | Description | Example |
|--------|-------------|---------|
| meta_key | The WooCommerce meta field name | "Accent Piece" |
| name_prefix | Text to add before the value (optional) | "Custom" |
| name_suffix | Text to add after the value (optional) | "Accent Piece" |
| sku_prefix | Prefix for generating SKUs | "accent-piece-" |
| price_field | Field name for price lookup | "accent_piece" |

### Example Transformations

Given this mapping:

```csv
meta_key,name_prefix,name_suffix,sku_prefix,price_field
Accent Piece,,Accent Piece,accent-piece-,accent_piece
```

These transformations will occur:

- Meta field `Accent Piece:Olive Wood` becomes line item `Olive Wood Accent Piece`
- SKU will be generated as `accent-piece-olive-wood`
- Price will be extracted from the order's meta data

### Adding New Meta Mappings

1. Open `meta_mapping.csv`
2. Add a new row for each meta field you want to convert
3. Leave prefix/suffix empty if not needed
4. Save the file and run the script

Example meta_mapping.csv:

```csv
meta_key,name_prefix,name_suffix,sku_prefix,price_field
Accent Piece,,Accent Piece,accent-piece-,accent_piece
Burr Set,,,burr-set-,burr_set
Optional Add-ons,,,addon-,addon
Custom Color,Custom,,color-,color_option
```

## Data Mapping

### Basic Order Fields

| WooCommerce Field | Shopify Field |
|-------------------|---------------|
| Order Number | Name |
| Customer Email | Email |
| Order Status | Financial Status |
| Order Status | Fulfillment Status |
| Currency | Currency |
| Order Date | Created at |

### Meta Fields to Line Items

| WooCommerce Meta | Shopify Line Item |
|-----------------|-------------------|
| meta:key:value | Separate line item with configured name |
| meta price data | Lineitem price |
| Generated SKU | Lineitem sku |

## Error Handling

The script includes comprehensive error handling for:

- Malformed CSV files
- Invalid JSON in address fields
- Missing required fields
- Incorrect date formats
- Malformed phone numbers
- Invalid variation data
- Missing meta mapping file
- Invalid meta field formats

## Limitations

- Does not migrate customer passwords
- Does not transfer product inventory
- Custom fields need manual mapping
- Order notes require additional configuration
- Refund history is not transferred
- Meta field prices must be in the order data

## Best Practices

1. Always backup your data before conversion
2. Test with a small batch first
3. Verify converted data in Shopify
4. Check meta mapping configuration
5. Keep original exports as backup
6. Review generated line items
7. Verify meta field prices are correct

## Troubleshooting

Common issues and solutions:

1. **Meta Fields Not Converting:**

   ```
   Warning: Meta mapping file not found
   ```

   - Verify meta_mapping.csv exists
   - Check CSV format is correct
   - Ensure meta keys match exactly

2. **Missing Prices:**

   ```
   Price data not found for meta item
   ```

   - Check meta price data in order
   - Verify price_field mapping

3. **Incorrect Name Formatting:**

   ```
   Unexpected line item name format
   ```

   - Review prefix/suffix configuration
   - Check for extra spaces
   - Verify meta value format
