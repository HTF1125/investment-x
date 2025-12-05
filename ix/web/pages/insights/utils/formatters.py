"""Formatting utility functions."""

from datetime import datetime
from typing import Optional


def format_date(date_str: Optional[str], format_str: str = "%Y-%m-%d") -> str:
    """Format date string to specified format."""
    if not date_str:
        return "Unknown"
    try:
        if isinstance(date_str, str) and len(date_str) >= 10:
            date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return date_obj.strftime(format_str)
        return str(date_str)
    except (ValueError, AttributeError):
        return str(date_str)


def format_date_for_display(date_str: Optional[str]) -> str:
    """Format date string for user-friendly display."""
    if not date_str:
        return "Unknown Date"
    try:
        if isinstance(date_str, str) and len(date_str) >= 10:
            date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return date_obj.strftime("%b %d, %Y")
        return str(date_str)
    except (ValueError, AttributeError):
        return str(date_str)


def truncate_text(text: Optional[str], max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
















