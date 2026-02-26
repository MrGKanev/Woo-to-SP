"""Standalone utility functions for WooCommerce to Shopify migration."""

import json
import re
from datetime import datetime
from typing import Any

import pandas as pd


def clean_text(text: Any) -> str:
    """Clean and normalize text content."""
    if pd.isna(text) or text is None:
        return ""
    return str(text).strip()


def create_handle(text: str) -> str:
    """Create URL-friendly handle from text."""
    if not text:
        return ""
    handle = str(text).lower()
    handle = re.sub(r"[^a-z0-9]+", "-", handle)
    return handle.strip("-")


def clean_phone(phone: Any) -> str:
    """Clean phone numbers to international format."""
    if pd.isna(phone) or not phone:
        return ""
    phone = re.sub(r"[^\d+]", "", str(phone))
    if not phone.startswith("+"):
        if len(phone) == 10:
            phone = "+1" + phone
    return phone


def clean_html(html_content: str) -> str:
    """Clean HTML content while preserving basic structure."""
    if not html_content:
        return ""

    html_content = html_content.replace("&nbsp;", " ")
    html_content = html_content.replace("&amp;", "&")
    html_content = html_content.replace("&quot;", '"')

    html_content = re.sub(r"<script.*?</script>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"<style.*?</style>", "", html_content, flags=re.DOTALL)

    # Remove WordPress shortcodes
    html_content = re.sub(r"\[[^\]]+\]", "", html_content)

    # Preserve line breaks
    html_content = html_content.replace("</p>", "</p>\n")
    html_content = html_content.replace("<br", "\n<br")

    # Remove remaining HTML tags
    html_content = re.sub(r"<[^>]+>", "", html_content)

    # Clean up whitespace
    html_content = re.sub(r"\s+", " ", html_content)

    return html_content.strip()


def format_date(date_str: str, output_format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format date string to standard format."""
    if not date_str:
        return ""

    input_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for fmt in input_formats:
        try:
            dt = datetime.strptime(str(date_str).strip(), fmt)
            return dt.strftime(output_format)
        except ValueError:
            continue

    return ""


def parse_json_field(field: Any, default: Any = None) -> Any:
    """Safely parse a JSON field that might be string or already parsed."""
    if pd.isna(field) or field is None:
        return default if default is not None else {}

    if isinstance(field, (dict, list)):
        return field

    if isinstance(field, str):
        try:
            return json.loads(field)
        except json.JSONDecodeError:
            return default if default is not None else {}

    return default if default is not None else {}
