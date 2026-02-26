# Woo-to-SP: WooCommerce to Shopify Migration Toolkit

A Python toolkit for migrating WooCommerce and MailChimp data to Shopify CSV format. Supports products, customers, orders, categories/collections, reviews, and discount codes.

## Features

- **Products** - Complete product data, variants, images, inventory, SEO
- **Customers** - WooCommerce customers + MailChimp subscriber import with deduplication
- **Orders** - Full order history with line items, meta fields, tax and shipping
- **Collections** - Category hierarchy, smart/manual collections, collection rules
- **Reviews** - Ratings, verified buyer status, product mapping
- **Discount Codes** - Coupon conversion with usage limits, product restrictions, date ranges

## Prerequisites

- Python 3.9+
- WooCommerce/WordPress CSV exports
- MailChimp exports (optional, for subscriber migration)

## Installation

```bash
git clone https://github.com/MrGKanev/Woo-to-SP.git
cd Woo-to-SP
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

All commands follow the same pattern:

```bash
woo-to-sp <command> -i <input.csv> -o <output.csv> [options]
```

### Products

```bash
woo-to-sp products -i woo_products.csv -o shopify_products.csv
woo-to-sp products -i woo_products.csv -o shopify_products.csv --skip-drafts --no-images
woo-to-sp products -i woo_products.csv -o shopify_products.csv -m image_mapping.csv
```

### Customers

```bash
woo-to-sp customers -w woo_customers.csv -o shopify_customers.csv
woo-to-sp customers -w woo_customers.csv -m mailchimp_export.zip -o shopify_customers.csv
```

### Orders

```bash
woo-to-sp orders -i woo_orders.csv -o shopify_orders.csv
woo-to-sp orders -i woo_orders.csv -o shopify_orders.csv -m meta_mapping.csv
```

### Collections

```bash
woo-to-sp collections -i woo_categories.csv -o shopify_collections.csv
woo-to-sp collections -i woo_categories.csv -o shopify_collections.csv --manual-collections
```

### Reviews

```bash
woo-to-sp reviews -i woo_reviews.csv -o shopify_reviews.csv
woo-to-sp reviews -i woo_reviews.csv -o shopify_reviews.csv -m product_mapping.csv
```

### Discounts

```bash
woo-to-sp discounts -i woo_coupons.csv -o shopify_discounts.csv
woo-to-sp discounts -i woo_coupons.csv -o shopify_discounts.csv --min-amount 25
```

### Global Options

| Option | Description |
|--------|-------------|
| `--verbose` / `-v` | Enable verbose logging output |
| `--dry-run` | Validate and transform without writing output files |
| `--help` | Show help for any command |

You can also run via module:

```bash
python -m woo_to_sp products -i input.csv -o output.csv
```

## Project Structure

```
Woo-to-SP/
├── src/woo_to_sp/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Typer CLI with Rich output
│   ├── config.py            # Pydantic configuration models
│   ├── utils.py             # Standalone utility functions
│   ├── base/
│   │   └── base_migration.py  # Abstract base class
│   ├── products/
│   │   └── products.py
│   ├── customers/
│   │   └── customers.py
│   ├── orders/
│   │   └── orders.py
│   ├── categories/
│   │   └── categories.py
│   ├── reviews/
│   │   └── review.py
│   └── promocodes/
│       └── promocode.py
├── tests/
│   ├── conftest.py
│   ├── test_base.py
│   ├── test_products.py
│   ├── test_customers.py
│   ├── test_orders.py
│   ├── test_collections.py
│   ├── test_reviews.py
│   ├── test_discounts.py
│   └── test_cli.py
└── pyproject.toml
```

## Required Export Files

### From WooCommerce

- Products export (CSV)
- Customer export (CSV)
- Order export (CSV)
- Category export (CSV)
- Review export (CSV)
- Coupon export (CSV)

### From MailChimp (Optional)

- Audience export (CSV or ZIP)
- Merge fields export
- Segments export

## Reporting

Each migration generates a JSON report in the `reports/` directory with:

- Success/failure statistics
- Error details for failed rows
- Processing duration
- Configuration used

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=woo_to_sp

# Format code
black src/ tests/

# Lint
ruff check src/ tests/
```

## License

MIT License - see the LICENSE file for details.
