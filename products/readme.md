# WooCommerce to Shopify Product Migration Tool

A robust Python tool for migrating WooCommerce products to Shopify, handling product variants, images, inventory, and more with detailed error tracking and reporting.

## 🌟 Features

- 📦 Complete product data migration
  - Basic product information
  - SEO-friendly handles
  - HTML content cleaning
  - Product status handling
  
- 🔄 Advanced variant support
  - Up to 3 variant options
  - SKU management
  - Price and inventory tracking
  - Weight and dimensions
  
- 🖼️ Image handling
  - Multiple product images
  - Position ordering
  - URL validation
  - Optional CDN URL mapping
  
- 📊 Comprehensive reporting
  - Detailed migration logs
  - Success/failure statistics
  - Progress tracking
  - Error documentation

## 📋 Prerequisites

- Python 3.8+
- Required packages:

  ```
  pandas>=2.1.0
  pathlib>=1.0.1
  typing>=3.7.4.3
  ```

- WooCommerce product export (CSV format)
- Sufficient disk space for logs and output files

## ⚙️ Configuration

The tool accepts the following configuration options:

```python
config = {
    'image_migration': True,      # Enable/disable image processing
    'inventory_tracking': True,    # Enable/disable inventory tracking
    'default_weight_unit': 'kg',  # Default weight unit if not specified
    'batch_size': 100,           # Number of products to process in each batch
    'skip_drafts': False         # Skip draft products during migration
}
```

## 📥 Input Format

### WooCommerce Products Export (woo_products_export.csv)

Required columns:

```csv
ID,post_title,post_content,post_status,sku,price,regular_price,stock_quantity,weight,images,variations
```

Example:

```csv
ID,post_title,post_content,post_status,sku,price,regular_price,stock_quantity,weight,images,variations
1,"Classic T-Shirt","<p>Comfortable cotton t-shirt</p>","publish","TS-001",19.99,24.99,100,0.2,"[""http://example.com/img1.jpg""]","[{""sku"":""TS-001-S"",""price"":19.99,""attribute_1"":""Small""}]"
```

### Image Mapping File (Optional - image_mapping.csv)

```csv
woo_url,shopify_url
http://example.com/img1.jpg,https://cdn.shopify.com/image1.jpg
```

## 📤 Output Format

The tool generates a Shopify-compatible CSV file with the following structure:

```csv
Handle,Title,Body (HTML),Vendor,Type,Tags,Published,Option1 Name,Option2 Name,Option3 Name,Variant 1 SKU,Variant 1 Price,Image 1 Src
classic-t-shirt,Classic T-Shirt,Comfortable cotton t-shirt,MyBrand,Apparel,cotton;casual,true,Size,Color,,TS-001-S,19.99,https://cdn.shopify.com/image1.jpg
```

## 💻 Usage

### Basic Usage

```python
from product_migration import ProductMigrationTool

tool = ProductMigrationTool()
tool.convert_products(
    input_file="data/input/woo_products_export.csv",
    output_file="data/output/shopify_products_import.csv"
)
```

### Advanced Usage

```python
config = {
    'image_migration': True,
    'inventory_tracking': True,
    'default_weight_unit': 'kg',
    'batch_size': 50,
    'skip_drafts': True
}

tool = ProductMigrationTool(config)
tool.convert_products(
    input_file="data/input/woo_products_export.csv",
    output_file="data/output/shopify_products_import.csv",
    image_mapping_file="data/input/image_mapping.csv"
)
```

## 📊 Reports

The tool generates detailed JSON reports:

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
  "success_rate": "95.00%",
  "configuration": {
    "image_migration": true,
    "inventory_tracking": true
  }
}
```

## 🔍 Troubleshooting

### Common Issues

1. Missing Product Data

```
Warning: Product missing required fields
```

Solution: Ensure all required fields are present in the WooCommerce export

2. Image Processing

```
Error: Invalid image URL format
```

Solution: Verify image URLs are accessible and properly formatted

3. Variant Data

```
Warning: Invalid variant structure
```

Solution: Check variant JSON format in the export file

### Best Practices

1. 🔄 Always backup your data before migration
2. ✅ Test with a small batch first
3. 📋 Verify product data completeness
4. 🖼️ Ensure image URLs are accessible
5. 📊 Monitor migration logs
6. 💾 Keep error reports for troubleshooting

## 🚫 Limitations

- Maximum 3 variant options per product
- Images must be accessible via URL
- HTML content is simplified during cleaning
- Some advanced WooCommerce features may not have Shopify equivalents

## 🆘 Support

If you encounter issues:

1. Check the logs in the `logs` directory
2. Review the generated report
3. Verify input data format
4. Open an issue in the repository

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request
