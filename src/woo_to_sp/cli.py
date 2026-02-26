"""Woo-to-SP: WooCommerce to Shopify Migration CLI built with Typer + Rich."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from woo_to_sp.config import (
    CollectionConfig,
    CustomerConfig,
    DiscountConfig,
    OrderConfig,
    ProductConfig,
    ReviewConfig,
)

app = typer.Typer(
    name="woo-to-sp",
    help="WooCommerce to Shopify Migration Toolkit",
    add_completion=False,
)
console = Console()


def _print_summary(stats: dict, tool_name: str) -> None:
    """Print a Rich summary table after migration."""
    table = Table(title=f"{tool_name} Migration Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")

    skip_keys = {"start_time", "end_time"}
    for key, value in stats.items():
        if key in skip_keys:
            continue
        label = key.replace("_", " ").title()
        table.add_row(label, str(value))

    if stats.get("start_time") and stats.get("end_time"):
        duration = (stats["end_time"] - stats["start_time"]).total_seconds()
        table.add_row("Duration", f"{duration:.2f}s")

    console.print()
    console.print(table)


verbose_option = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
dry_run_option = typer.Option(False, "--dry-run", help="Validate and transform without writing output")


@app.command()
def products(
    input: Path = typer.Option(..., "--input", "-i", help="WooCommerce products CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="Shopify products CSV"),
    image_mapping: Optional[Path] = typer.Option(None, "--image-mapping", "-m", help="Image mapping CSV"),
    skip_drafts: bool = typer.Option(False, "--skip-drafts", help="Skip draft products"),
    no_images: bool = typer.Option(False, "--no-images", help="Disable image migration"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Migrate WooCommerce products to Shopify format."""
    config = ProductConfig(
        image_migration=not no_images,
        skip_drafts=skip_drafts,
        show_progress=True,
    )

    from woo_to_sp.products.products import ProductMigrationTool

    tool = ProductMigrationTool(config)
    if verbose:
        import logging

        for handler in tool.logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        tool.convert_products(
            input_file=str(input),
            output_file=str(output),
            image_mapping_file=str(image_mapping) if image_mapping else None,
            dry_run=dry_run,
        )
        _print_summary(tool.stats, "Product")
        console.print("[bold green]Product migration completed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Migration failed:[/] {e}")
        raise typer.Exit(code=1)


@app.command()
def customers(
    output: Path = typer.Option(..., "--output", "-o", help="Shopify customers CSV"),
    woo_file: Optional[Path] = typer.Option(None, "--woo-file", "-w", help="WooCommerce customers CSV"),
    mailchimp_folder: Optional[Path] = typer.Option(None, "--mailchimp-folder", "-m", help="MailChimp export folder/zip"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Migrate WooCommerce customers and MailChimp subscribers to Shopify format."""
    if not woo_file and not mailchimp_folder:
        console.print("[bold red]Error:[/] At least one of --woo-file or --mailchimp-folder is required")
        raise typer.Exit(code=1)

    config = CustomerConfig(show_progress=True)

    from woo_to_sp.customers.customers import CustomerMigrationTool

    tool = CustomerMigrationTool(config)
    if verbose:
        import logging

        for handler in tool.logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        tool.convert_customers(
            woo_file=str(woo_file) if woo_file else None,
            mailchimp_folder=str(mailchimp_folder) if mailchimp_folder else None,
            output_file=str(output),
            dry_run=dry_run,
        )
        _print_summary(tool.stats, "Customer")
        console.print("[bold green]Customer migration completed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Migration failed:[/] {e}")
        raise typer.Exit(code=1)


@app.command()
def orders(
    input: Path = typer.Option(..., "--input", "-i", help="WooCommerce orders CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="Shopify orders CSV"),
    meta_mapping: Optional[Path] = typer.Option(None, "--meta-mapping", "-m", help="Meta mapping CSV"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Migrate WooCommerce orders to Shopify format."""
    config = OrderConfig(show_progress=True)

    from woo_to_sp.orders.orders import OrderMigrationTool

    tool = OrderMigrationTool(config)
    if verbose:
        import logging

        for handler in tool.logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        tool.convert_orders(
            input_file=str(input),
            output_file=str(output),
            meta_mapping_file=str(meta_mapping) if meta_mapping else None,
            dry_run=dry_run,
        )
        _print_summary(tool.stats, "Order")
        console.print("[bold green]Order migration completed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Migration failed:[/] {e}")
        raise typer.Exit(code=1)


@app.command()
def collections(
    input: Path = typer.Option(..., "--input", "-i", help="WooCommerce categories CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="Shopify collections CSV"),
    image_mapping: Optional[Path] = typer.Option(None, "--image-mapping", "-m", help="Image mapping CSV"),
    manual_collections: bool = typer.Option(False, "--manual-collections", help="Use manual instead of smart collections"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Migrate WooCommerce categories to Shopify collections."""
    config = CollectionConfig(
        use_smart_collections=not manual_collections,
        show_progress=True,
    )

    from woo_to_sp.categories.categories import CollectionMigrationTool

    tool = CollectionMigrationTool(config)
    if verbose:
        import logging

        for handler in tool.logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        tool.convert_collections(
            input_file=str(input),
            output_file=str(output),
            image_mapping_file=str(image_mapping) if image_mapping else None,
            dry_run=dry_run,
        )
        _print_summary(tool.stats, "Collection")
        console.print("[bold green]Collection migration completed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Migration failed:[/] {e}")
        raise typer.Exit(code=1)


@app.command()
def reviews(
    input: Path = typer.Option(..., "--input", "-i", help="WooCommerce reviews CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="Shopify reviews CSV"),
    product_mapping: Optional[Path] = typer.Option(None, "--product-mapping", "-m", help="Product mapping CSV"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Migrate WooCommerce product reviews to Shopify format."""
    config = ReviewConfig(show_progress=True)

    from woo_to_sp.reviews.review import ReviewMigrationTool

    tool = ReviewMigrationTool(config)
    if verbose:
        import logging

        for handler in tool.logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        tool.convert_reviews(
            input_file=str(input),
            output_file=str(output),
            product_mapping_file=str(product_mapping) if product_mapping else None,
            dry_run=dry_run,
        )
        _print_summary(tool.stats, "Review")
        console.print("[bold green]Review migration completed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Migration failed:[/] {e}")
        raise typer.Exit(code=1)


@app.command()
def discounts(
    input: Path = typer.Option(..., "--input", "-i", help="WooCommerce coupons CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="Shopify discounts CSV"),
    product_mapping: Optional[Path] = typer.Option(None, "--product-mapping", "-m", help="Product mapping CSV"),
    min_amount: float = typer.Option(0, "--min-amount", help="Default minimum purchase amount"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Migrate WooCommerce coupons to Shopify discount codes."""
    config = DiscountConfig(
        default_minimum_amount=min_amount,
        show_progress=True,
    )

    from woo_to_sp.promocodes.promocode import DiscountMigrationTool

    tool = DiscountMigrationTool(config)
    if verbose:
        import logging

        for handler in tool.logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        tool.convert_discounts(
            input_file=str(input),
            output_file=str(output),
            product_mapping_file=str(product_mapping) if product_mapping else None,
            dry_run=dry_run,
        )
        _print_summary(tool.stats, "Discount")
        console.print("[bold green]Discount migration completed successfully![/]")
    except Exception as e:
        console.print(f"[bold red]Migration failed:[/] {e}")
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entry point."""
    app()
