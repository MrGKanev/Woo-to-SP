# WooCommerce to Shopify - Products Migration Tool

Convert WooCommerce products to Shopify format with full support for variants, images, pricing, and metadata.

## Features

- 📦 Complete product data migration
  - Basic product information
  - SEO-friendly handles
  - HTML content cleaning
  - Product status preservation
  
- 🔄 Advanced variant support
  - Up to 3 variant options
  - SKU management
  - Price and inventory tracking
  - Weight and dimensions
  
- 🖼️ Image handling
  - Multiple product images
  - Position ordering
  - URL validation
  - CDN URL mapping
  
- 🏷️ Metadata support
  - Product type mapping
  - Vendor preservation
  - Custom attributes
  - Tags migration

## Usage

1. **Basic Usage**

```bash
python main.py \
  --input woo_products_export.csv \
  --output shopify_products_import.csv \
  --image-mapping image_mapping.csv
```

2. **Configuration Options**

```python
config = {
    'image_migration': True,      # Enable/disable image processing
    'inventory_tracking': True,    # Enable/disable inventory tracking
    'default_weight_unit': 'kg',  # Default weight unit if not specified
    'batch_size': 100,           # Number of products to process in each batch
    'skip_drafts': False         # Skip draft products during migration
}

tool = ProductMigrationTool(config)
tool.convert_products(
    input_file="data/input/woo_products_export.csv",
    output_file="data/output/shopify_products_import.csv",
    image_mapping_file="data/input/image_mapping.csv"  # Optional
)
```

## Input Requirements

### Products Export (woo_products_export.csv)

Required columns:

```csv
ID,post_title,post_content,post_status,sku,price,regular_price,stock_quantity,weight,images,variations
```

Example:

```csv
ID,post_title,post_content,post_status,sku,price,regular_price,stock_quantity,weight,images,variations
1,"Classic T-Shirt","<p>Comfortable cotton t-shirt</p>","publish","TS-001",19.99,24.99,100,0.2,"[""http://example.com/img1.jpg""]","[{""sku"":""TS-001-S"",""price"":19.99,""attribute_1"":""Small""}]"
```

### Image Mapping (Optional - image_mapping.csv)

```csv
woo_url,shopify_url
http://example.com/img1.jpg,https://cdn.shopify.com/image1.jpg
```

## Output Format

Generates Shopify-compatible CSV with:

```csv
Handle,Title,Body (HTML),Vendor,Type,Tags,Published,Option1 Name,Option2 Name,Option3 Name,Variant 1 SKU,Variant 1 Price,Image 1 Src
classic-t-shirt,Classic T-Shirt,Comfortable cotton t-shirt,MyBrand,Apparel,cotton;casual,true,Size,Color,,TS-001-S,19.99,https://cdn.shopify.com/image1.jpg
```

## Data Processing

1. **Content Cleaning**
   - HTML tag removal
   - Shortcode processing
   - Special character handling
   - Line break preservation

2. **Image Processing**
   - URL validation
   - CDN mapping
   - Position ordering
   - Alt text generation

3. **Variant Handling**
   - Option mapping
   - SKU generation
   - Price tier preservation
   - Inventory tracking

4. **SEO Optimization**
   - Handle generation
   - Title formatting
   - Meta description cleaning
   - URL structure

## Best Practices

1. 🔄 Always backup your product data first
2. ✅ Test with a small batch (5-10 products)
3. 🖼️ Verify image URLs are accessible
4. 📋 Check variant structure completeness
5. 💰 Validate pricing across variants
6. 📊 Monitor migration logs
7. 🏷️ Review generated SKUs
8. 💾 Keep original exports as backup

## Error Handling

The tool handles:

- Missing required fields
- Malformed CSV files
- Invalid JSON data
- Inaccessible images
- Duplicate SKUs
- Invalid pricing
- Variant misconfigurations
- HTML parsing errors

## Limitations

- Maximum 3 variant options per product
- Images must be accessible via URL
- HTML content is simplified
- Some custom fields may need manual mapping
- Product relationships need manual setup
- Download digital products separately

## Reports

Generated JSON reports include:

```json
{
  "timestamp": "2024-01-15T14:30:00",
  "statistics": {
    "total_products": 100,
    "successful": 95,
    "failed": 3,
    "warnings": 2,
    "variants_processed": 250,
    "images_processed": 180
  },
  "success_rate": "95.00%"
}
```

## Support

See main project README for general help. For product-specific issues:

1. Check logs/product_migration_[timestamp].log
2. Review reports/product_migration_report_[timestamp].json
3. Verify product export format matches requirements
4. Ensure all variant data is complete
5. Validate image URLs are accessible

## Troubleshooting

Common issues and solutions:

1. **Missing Images**

```
Warning: Image URL not accessible
```

Solution: Verify image URLs in mapping file or source export

2. **Variant Issues**

```
Warning: Invalid variant structure
```

Solution: Check variant JSON format in export file

3. **Price Formatting**

- Images must be accessible via URL
```
Error: Invalid price format
```

Solution: Ensure prices are numeric and use correct decimal format
