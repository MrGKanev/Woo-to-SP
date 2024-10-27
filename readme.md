# WooCommerce to Shopify (Woo-to-SP) Migration Tools

A comprehensive Python toolkit for migrating WooCommerce and MailChimp data to Shopify, including products, customers, orders, categories/collections, reviews, and discount codes.

## 🌟 Features

### Products Migration

- Complete product data migration
- Advanced variant support
- Image handling and CDN mapping
- SEO data preservation

### Customers Migration

- WooCommerce customers conversion
- MailChimp subscribers integration
- Address formatting
- Marketing preferences

### Orders Migration

- Full order history transfer
- Custom meta field mapping
- Line item preservation
- Tax and shipping details

### Collections Migration

- Category hierarchy preservation
- Smart collection rules
- SEO data migration
- Image handling

### Reviews Migration

- Rating preservation
- Verified buyer status
- Review metadata
- Customer information

### Discount Codes Migration

- Coupon code conversion
- Usage limits
- Product restrictions
- Date range preservation

## 📋 Prerequisites

- Python 3.8+
- Required packages (install via `pip install -r requirements.txt`)
- WooCommerce/WordPress exports
- MailChimp exports (if migrating subscribers)

## 🚀 Quick Start

1. Clone the repository:

```bash
git clone <repository-url>
cd woo-to-sp-migration
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Choose your migration tool:

```bash
cd [products|customers|orders|collections|reviews|discounts]
python main.py
```

## 📁 Project Structure

```
woo-to-sp/
├── requirements.txt
├── LICENSE
├── README.md
├── products/
│   ├── README.md
│   └── main.py
├── customers/
│   ├── README.md
│   └── main.py
├── orders/
│   ├── README.md
│   └── main.py
├── collections/
│   ├── README.md
│   └── main.py
├── reviews/
│   ├── README.md
│   └── main.py
└── discounts/
    ├── README.md
    └── main.py
```

## 📥 Required Export Files

### From WooCommerce

- Products export (CSV)
- Customer export (CSV)
- Order export (CSV)
- Category export (CSV)
- Review export (CSV)
- Coupon export (CSV)

### From MailChimp (Optional)

- Audience export (CSV)
- Merge fields export
- Segments export

## 🎯 Migration Process

1. Export data from WooCommerce/MailChimp
2. Configure mapping files if needed
3. Run appropriate migration tool
4. Review generated reports
5. Import data into Shopify

## 📊 Reporting

Each tool generates detailed reports including:

- Success/failure statistics
- Warning messages
- Processing timestamps
- Configuration details

## ⚠️ Common Issues

1. **Export Format Issues**
   - Ensure exports are in correct CSV format
   - Verify required columns are present

2. **Character Encoding**
   - Use UTF-8 encoding for all files
   - Check for special character handling

3. **Memory Usage**
   - Process large datasets in batches
   - Monitor system resources

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request
4. Follow coding standards

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. Check tool-specific README
2. Review generated logs
3. Open an issue in the repository
