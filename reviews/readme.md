# WooCommerce to Shopify - Reviews Migration Tool

Convert WooCommerce product reviews to Shopify review format.

## Features

- ⭐ Rating preservation
- ✅ Verified buyer status
- 👤 Customer information
- 📅 Review dates
- 🏷️ Product mapping
- 📊 Detailed reporting
- 🔍 Content validation

## Usage

1. **Basic Usage**

```bash
python main.py \
  --input woo_reviews_export.csv \
  --output shopify_reviews_import.csv \
  --product-mapping product_mapping.csv
```

2. **Configuration Example**

```python
config = {
    'input_file': 'woo_reviews_export.csv',
    'output_file': 'shopify_reviews_import.csv',
    'product_mapping_file': 'product_mapping.csv'
}
```

## Input Requirements

### Reviews Export

Required fields:

- comment_ID
- comment_post_ID
- comment_author
- comment_content
- comment_date
- rating
- comment_author_email

### Product Mapping (Optional)

```csv
woo_id,shopify_handle
123,classic-t-shirt
456,summer-dress
```

## Output Format

Generates Shopify-compatible CSV with:

- Product Handle
- Review Date
- Reviewer Name
- Reviewer Email
- Review Title
- Rating
- Review Text
- Review Status
- Verified Buyer Status

## Best Practices

1. ✅ Export fresh review data
2. 🔄 Test with small batch
3. 📋 Verify product mapping
4. 💾 Keep original exports
5. 📊 Monitor migration logs

## Limitations

- Cannot migrate review responses
- Limited to text content
- No image migration
- Review votes not transferred
- Customer history links lost

## Support

See main project README for general help. For review-specific issues:

1. Check logs/review_migration_[timestamp].log
2. Review reports/review_migration_report_[timestamp].json
3. Verify review export format matches requirements
