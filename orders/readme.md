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

2. Run the conversion script:

```python
from woo_to_shopify_orders import convert_woo_to_shopify

convert_woo_to_shopify(
    input_file="woocommerce_orders_export.csv",
    output_file="shopify_orders_import.csv"
)
```

## Data Mapping

| WooCommerce Field | Shopify Field |
|-------------------|---------------|
| Order Number | Name |
| Customer Email | Email |
| Order Status | Financial Status |
| Order Status | Fulfillment Status |
| Currency | Currency |
| Order Date | Created at |

### Product Variations

The script handles WooCommerce variations in the following formats:

```json
{
    "attribute_pa_size": "large",
    "attribute_pa_color": "blue"
}
```

Converts to Shopify format:

```
Lineitem variant title: Blue / Large
Lineitem option1 name: Color
Lineitem option1 value: Blue
Lineitem option2 name: Size
Lineitem option2 value: Large
```

## Error Handling

The script includes comprehensive error handling for:

- Malformed CSV files
- Invalid JSON in address fields
- Missing required fields
- Incorrect date formats
- Malformed phone numbers
- Invalid variation data

## Limitations

- Does not migrate customer passwords
- Does not transfer product inventory
- Custom fields need manual mapping
- Order notes require additional configuration
- Refund history is not transferred

## Best Practices

1. Always backup your data before conversion
2. Test with a small batch first
3. Verify converted data in Shopify
4. Check for missing information
5. Keep original exports as backup

## Troubleshooting

Common issues and solutions:

1. **Variation Data Not Converting:**

   ```
   Error parsing variation attributes
   ```

   - Check variation format in export
   - Ensure all attributes are properly named

2. **Missing Line Items:**

   ```
   Warning: Could not parse line items for order
   ```

   - Verify line items format in export
   - Check for JSON formatting issues
