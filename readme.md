# WooCommerce to Shopify Orders Converter

A Python script that converts WooCommerce order export files into Shopify-compatible CSV format for seamless order migration between platforms.

## Prerequisites

- Python 3.6 or higher
- pandas library (`pip install pandas`)
- WooCommerce Order Export CSV file (from "Order Import Export for WooCommerce" plugin)

## Installation

1. Clone this repository or download the script:

```bash
git clone https://github.com/MrGKanev/Woo-to-SP
# or download woo_to_shopify.py directly
```

2. Install required dependencies:

```bash
pip install pandas
```

## Usage

1. First, export your WooCommerce orders:
   - Install the "Order Import Export for WooCommerce" plugin from WordPress.org
   - Go to WooCommerce > Export/Import Orders
   - Export your orders as CSV

2. Run the conversion script:

```python
from woo_to_shopify import convert_woo_to_shopify

# Convert your orders
convert_woo_to_shopify(
    input_file="woocommerce_orders_export.csv",
    output_file="shopify_orders_import.csv"
)
```

3. The script will generate a Shopify-compatible CSV file that you can import through the Shopify admin panel.

## Features

- Converts basic order information
- Handles customer details
- Processes billing and shipping addresses
- Converts order statuses
- Maintains line items (products)
- Preserves tax and shipping information
- Formats phone numbers to international standard
- Handles date formatting
- Supports currency conversion
- Includes error handling and validation

## Data Mapping

### WooCommerce to Shopify Field Mapping

| WooCommerce Field | Shopify Field |
|-------------------|---------------|
| Order Number | Name |
| Customer Email | Email |
| Order Status | Financial Status |
| Order Status | Fulfillment Status |
| Currency | Currency |
| Order Date | Created at |
| Billing Address | Billing Name, Street, etc. |
| Shipping Address | Shipping Name, Street, etc. |
| Line Items | Lineitem name, quantity, price |
| Total Tax | Tax 1 Value |
| Shipping Method | Shipping Line Title |
| Shipping Total | Shipping Line Price |
| Order Total | Total |

## Error Handling

The script includes error handling for:

- Malformed CSV files
- Invalid JSON in address fields
- Missing required fields
- Incorrect date formats
- Malformed phone numbers

If an error occurs, the script will print a detailed error message explaining the issue.

## Limitations

- Does not migrate customer passwords
- Does not transfer product inventory
- Custom fields may need manual mapping
- Order notes and custom meta data require additional configuration
- Refund history is not transferred

## Best Practices

1. Always backup your data before running the conversion
2. Test with a small batch of orders first
3. Verify the converted data in Shopify before importing large datasets
4. Check for any missing or incorrect information after import
5. Keep original WooCommerce exports as backup

## Troubleshooting

Common issues and solutions:

1. **Missing Fields**: Ensure your WooCommerce export includes all required fields
2. **Date Format Errors**: Check that dates are in a standard format
3. **Character Encoding**: Use UTF-8 encoding for your CSV files
4. **Large Files**: For large datasets, consider processing in batches

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or need assistance:

1. Check the troubleshooting section
2. Review your input data format
3. Verify all prerequisites are met
4. Open an issue in the repository
