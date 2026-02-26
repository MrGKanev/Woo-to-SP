"""Tests for the CLI interface."""

import csv
from pathlib import Path

import pytest
from typer.testing import CliRunner

from woo_to_sp.cli import app

runner = CliRunner()


@pytest.fixture
def products_csv(tmp_path):
    """Create a minimal products CSV."""
    csv_file = tmp_path / "products.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["ID", "post_title", "post_content", "status", "variations", "images"],
        )
        writer.writeheader()
        writer.writerow({
            "ID": "1",
            "post_title": "Test Product",
            "post_content": "A description",
            "status": "publish",
            "variations": "[]",
            "images": "[]",
        })
    return csv_file


@pytest.fixture
def customers_csv(tmp_path):
    """Create a minimal customers CSV."""
    csv_file = tmp_path / "customers.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Email", "First Name", "Last Name"])
        writer.writeheader()
        writer.writerow({
            "Email": "test@example.com",
            "First Name": "John",
            "Last Name": "Doe",
        })
    return csv_file


@pytest.fixture
def orders_csv(tmp_path):
    """Create a minimal orders CSV."""
    csv_file = tmp_path / "orders.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["order_number", "customer_email", "status", "line_item_1", "order_total"],
        )
        writer.writeheader()
        writer.writerow({
            "order_number": "1001",
            "customer_email": "test@example.com",
            "status": "completed",
            "line_item_1": "name:Widget|quantity:1|total:9.99|sku:W1",
            "order_total": "9.99",
        })
    return csv_file


@pytest.fixture
def categories_csv(tmp_path):
    """Create a minimal categories CSV."""
    csv_file = tmp_path / "categories.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "slug", "description"])
        writer.writeheader()
        writer.writerow({
            "name": "Electronics",
            "slug": "electronics",
            "description": "Electronic items",
        })
    return csv_file


@pytest.fixture
def reviews_csv(tmp_path):
    """Create a minimal reviews CSV."""
    csv_file = tmp_path / "reviews.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "comment_ID",
                "comment_post_ID",
                "comment_author",
                "comment_content",
                "rating",
                "comment_approved",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "comment_ID": "1",
            "comment_post_ID": "101",
            "comment_author": "John",
            "comment_content": "Great!",
            "rating": "5",
            "comment_approved": "1",
        })
    return csv_file


@pytest.fixture
def coupons_csv(tmp_path):
    """Create a minimal coupons CSV."""
    csv_file = tmp_path / "coupons.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["code", "discount_type", "amount", "enabled"],
        )
        writer.writeheader()
        writer.writerow({
            "code": "TEST10",
            "discount_type": "percent",
            "amount": "10",
            "enabled": "yes",
        })
    return csv_file


class TestCLIHelp:
    def test_main_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "WooCommerce to Shopify" in result.stdout

    def test_products_help(self):
        result = runner.invoke(app, ["products", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.stdout
        assert "--output" in result.stdout

    def test_customers_help(self):
        result = runner.invoke(app, ["customers", "--help"])
        assert result.exit_code == 0

    def test_orders_help(self):
        result = runner.invoke(app, ["orders", "--help"])
        assert result.exit_code == 0

    def test_collections_help(self):
        result = runner.invoke(app, ["collections", "--help"])
        assert result.exit_code == 0

    def test_reviews_help(self):
        result = runner.invoke(app, ["reviews", "--help"])
        assert result.exit_code == 0

    def test_discounts_help(self):
        result = runner.invoke(app, ["discounts", "--help"])
        assert result.exit_code == 0


class TestCLIExecution:
    def test_products_command(self, products_csv, tmp_path):
        output = tmp_path / "out_products.csv"
        result = runner.invoke(
            app,
            ["products", "-i", str(products_csv), "-o", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_products_dry_run(self, products_csv, tmp_path):
        output = tmp_path / "out_products.csv"
        result = runner.invoke(
            app,
            ["products", "-i", str(products_csv), "-o", str(output), "--dry-run"],
        )
        assert result.exit_code == 0
        assert not output.exists()

    def test_customers_command(self, customers_csv, tmp_path):
        output = tmp_path / "out_customers.csv"
        result = runner.invoke(
            app,
            ["customers", "-w", str(customers_csv), "-o", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_customers_no_source_fails(self, tmp_path):
        output = tmp_path / "out.csv"
        result = runner.invoke(app, ["customers", "-o", str(output)])
        assert result.exit_code == 1

    def test_orders_command(self, orders_csv, tmp_path):
        output = tmp_path / "out_orders.csv"
        result = runner.invoke(
            app,
            ["orders", "-i", str(orders_csv), "-o", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_collections_command(self, categories_csv, tmp_path):
        output = tmp_path / "out_collections.csv"
        result = runner.invoke(
            app,
            ["collections", "-i", str(categories_csv), "-o", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_reviews_command(self, reviews_csv, tmp_path):
        output = tmp_path / "out_reviews.csv"
        result = runner.invoke(
            app,
            ["reviews", "-i", str(reviews_csv), "-o", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_discounts_command(self, coupons_csv, tmp_path):
        output = tmp_path / "out_discounts.csv"
        result = runner.invoke(
            app,
            ["discounts", "-i", str(coupons_csv), "-o", str(output)],
        )
        assert result.exit_code == 0
        assert output.exists()

    def test_products_nonexistent_input(self, tmp_path):
        output = tmp_path / "out.csv"
        result = runner.invoke(
            app,
            ["products", "-i", "/nonexistent/file.csv", "-o", str(output)],
        )
        assert result.exit_code == 1
