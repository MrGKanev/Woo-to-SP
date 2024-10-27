# WooCommerce to Shopify - Collections Migration Tool

Convert WordPress/WooCommerce categories and taxonomies to Shopify collections.

## Features

- 📁 Category to collection conversion
- 🌳 Hierarchy preservation
- 🤖 Smart collection rules
- 🖼️ Image handling
- 🔍 SEO data migration
- 🔄 Parent-child relationships
- 📊 Detailed reporting

## Usage

1. **Basic Usage**

```bash
python main.py \
  --input wp_categories_export.csv \
  --output sp_collections_import.csv \
  --image-mapping category_images.csv
```

2. **Configuration Example**

```python
config = {
    'use_smart_collections': True,
    'input_file': 'wp_categories_export.csv',
    'output_file': 'sp_collections_import.csv',
    'image_mapping_file': 'category_images.csv'
}
```

## Input Format

### Categories Export

```csv
term_id,name,slug,description,parent,image,seo_title,seo_description
1,Men,men,Men's clothing,0,http://example.com/image.jpg,Men's Fashion,Shop men's clothing
```

### Image Mapping (Optional)

```csv
category_id,image_url
1,https://cdn.shopify.com/category-image-1.jpg
```

## Output Format

Generates Shopify-compatible CSV with:

- Handle
- Title
- Body HTML
- Collection Type
- Published Status
- Image Source
- Sort Order
- SEO Data
- Collection Rules

## Smart Collections

Automatically creates rules based on:

- Category slugs (tags)
- Product types
- Custom attributes

## Best Practices

1. 💾 Backup category data
2. ✅ Test with small set
3. 🖼️ Verify image URLs
4. 📋 Check parent-child links
5. 🔍 Review collection rules
6. 📊 Monitor logs

## Limitations

- Cannot migrate custom fields
- Image URL migration only
- Limited hierarchy depth
- Rule conditions limited to Shopify's options

## Support

See main project README for general help. For collection-specific issues:

1. Check logs/collection_migration_[timestamp].log
2. Review reports/collection_migration_report_[timestamp].json
3. Verify category export format
