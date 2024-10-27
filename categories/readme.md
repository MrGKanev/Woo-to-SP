# WP to SP Collections Migration Tool

A Python tool for migrating WordPress/WooCommerce categories and taxonomies to Shopify collections with smart collection rules, hierarchy preservation, and image handling.

## 🌟 Features

- ✨ Converts categories to collections
- 🌳 Preserves category hierarchy
- 🤖 Creates smart collection rules
- 🖼️ Handles category images
- 🔍 Maintains SEO data
- 🧹 Automatic content cleaning
- 📊 Detailed migration reports
- 🚨 Comprehensive error handling
- 🔄 Parent-child relationship management
- 🏷️ Tag-based collection rules

## 📋 Prerequisites

- Python 3.8+
- WordPress/WooCommerce category export in CSV format
- Sufficient permissions to access category images

## 📝 Input Format Requirements

### Categories Export (wp_categories_export.csv)

```csv
term_id,name,slug,description,parent,image,seo_title,seo_description
1,Men,men,Men's clothing,0,http://example.com/image.jpg,Men's Fashion,Shop men's clothing
```

### Image Mapping (Optional - category_images.csv)

```csv
category_id,image_url
1,https://example.com/category-image-1.jpg
2,https://example.com/category-image-2.jpg
```

## 💻 Usage

### Basic Usage

```python
from src.wp_sp_collections import CollectionMigrationTool

tool = CollectionMigrationTool()
tool.convert_collections(
    input_file="data/input/wp_categories_export.csv",
    output_file="data/output/sp_collections_import.csv"
)
```

### Advanced Usage with Configuration

```python
config = {
    'use_smart_collections': True,
    'input_file': 'data/input/wp_categories_export.csv',
    'output_file': 'data/output/sp_collections_import.csv',
    'image_mapping_file': 'data/input/category_images.csv'
}

tool = CollectionMigrationTool(config)
tool.convert_collections(
    input_file=config['input_file'],
    output_file=config['output_file'],
    image_mapping_file=config['image_mapping_file']
)
```

## 📤 Output Format

The tool generates a Shopify-compatible CSV with these columns:

```csv
Handle,Title,Body HTML,Collection Type,Published,Image Src,Sort Order,Template Suffix,Published Scope,SEO Title,SEO Description,Rules
mens-clothing,Men,Men's clothing,smart,TRUE,https://example.com/men.jpg,best-selling,,web,Men's Fashion,Shop men's clothing,"[{""column"":""type"",""relation"":""equals"",""condition"":""Men""}]"
```

## 📊 Reports

Each migration generates a detailed JSON report including:

```json
{
  "timestamp": "2024-01-15T14:30:00",
  "statistics": {
    "total_collections": 100,
    "successful": 98,
    "failed": 1,
    "warnings": 1,
    "rules_created": 95
  },
  "success_rate": "98.00%",
  "configuration": {
    "use_smart_collections": true,
    "image_mapping_used": true
  }
}
```

## 📝 Logging

Comprehensive logging includes:

- Migration progress
- Error tracking
- Warning messages
- Validation results
- Collection rule creation

## ⚠️ Error Handling

The tool handles various scenarios:

- Missing required fields
- Invalid image URLs
- Broken parent-child relationships
- Duplicate handles
- Malformed data

## ⚡ Smart Collections

Automatically creates collection rules based on:

- Category slugs (tags)
- Product types
- Custom attributes

## 🔄 Data Cleaning

Automatic cleaning of:

- HTML content
- WordPress shortcodes
- Image URLs
- SEO metadata

## 🚫 Limitations

- Cannot migrate custom category fields
- Limited to image URL migration (no file transfer)
- Hierarchy limited to Shopify's constraints
- Smart collection rules limited to Shopify's conditions

## ✅ Best Practices

1. Always backup your data before migration
2. Test with a small category set first
3. Verify image URLs are accessible
4. Check parent-child relationships
5. Review generated collection rules
6. Monitor the migration logs
7. Validate the output in Shopify

## 🔍 Troubleshooting

Common issues and solutions:

### Missing Images

```
Warning: Image URL not accessible
```

Solution: Verify image URLs in mapping file or source export

### Parent Category Issues

```
Warning: Parent category not found
```

Solution: Ensure all parent categories are included in export

### Handle Conflicts

```
Warning: Duplicate handle generated
```

Solution: Unique handles are automatically created with hash suffixes
