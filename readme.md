# WooCommerce to Shopify Migration Tools

A collection of Python scripts to help migrate data from WooCommerce and MailChimp to Shopify.

## Overview

This toolkit provides two main migration tools:

1. [Order Migration Tool](orders/README.md) - Converts WooCommerce orders to Shopify format
2. [Customer Migration Tool](customers/README.md) - Converts WooCommerce customers and MailChimp subscribers to Shopify customers

## Prerequisites

- Python 3.6 or higher
- pandas library (`pip install pandas`)
- WooCommerce export files (orders and/or customers)
- MailChimp export files (optional)

## Quick Start

1. Clone this repository:

```bash
git clone <repository-url>
cd woo-to-shopify-migration
```

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Choose your migration tool:
   - For orders: See [Order Migration Guide](orders/README.md)
   - For customers: See [Customer Migration Guide](customers/README.md)

## Project Structure

```
woo-to-shopify-migration/
├── README.md
├── requirements.txt
├── orders/
│   ├── README.md
│   └── woo_to_shopify_orders.py
└── customers/
    ├── README.md
    └── woo_to_shopify_customers.py
```

## Getting Export Files

### WooCommerce Exports

1. Orders:
   - Install "Order Import Export for WooCommerce" plugin
   - Go to WooCommerce > Export/Import Orders
   - Export orders as CSV

2. Customers:
   - Go to WooCommerce > Customers
   - Use the built-in export function
   - Save as CSV

### MailChimp Export

1. Log in to your MailChimp account
2. Go to Audience > All Contacts
3. Click "Export Audience"
4. Choose "Export as CSV"
5. For full data, select "Export audience data plus all subscriber activity"

## Common Issues

1. Missing Files:

   ```
   FileNotFoundError: [Errno 2] No such file or directory
   ```

   - Ensure all required export files are in the correct location
   - Check file permissions

2. Import Errors:

   ```
   ImportError: No module named 'pandas'
   ```

   - Run `pip install -r requirements.txt`

3. Data Format Issues:

   ```
   ValueError: Time data does not match format
   ```

   - Ensure your WooCommerce and MailChimp exports are in the expected format
   - Check the specific tool's README for format requirements

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues:

1. Check the specific tool's README
2. Review the Troubleshooting section
3. Open an issue in the repository

