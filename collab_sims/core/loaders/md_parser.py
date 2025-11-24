"""Markdown parser with YAML frontmatter support.

This module provides utilities to parse markdown files that contain
YAML frontmatter metadata.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class MarkdownDocument:
    """Represents a parsed markdown document with frontmatter."""

    frontmatter: dict[str, Any]
    content: str
    raw_content: str  # Full original content including frontmatter


def parse_markdown_with_frontmatter(file_path: str | Path) -> MarkdownDocument:
    """Parse a markdown file with YAML frontmatter.

    Args:
        file_path: Path to the markdown file

    Returns:
        MarkdownDocument with parsed frontmatter and content

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If frontmatter YAML is invalid
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    raw_content = file_path.read_text(encoding="utf-8")

    # Check if file has frontmatter (starts with ---)
    if not raw_content.startswith("---"):
        # No frontmatter, return empty dict
        return MarkdownDocument(
            frontmatter={},
            content=raw_content.strip(),
            raw_content=raw_content,
        )

    # Split frontmatter and content
    parts = raw_content.split("---", 2)

    if len(parts) < 3:
        # Invalid frontmatter format
        return MarkdownDocument(
            frontmatter={},
            content=raw_content.strip(),
            raw_content=raw_content,
        )

    frontmatter_text = parts[1].strip()
    content = parts[2].strip()

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML frontmatter in {file_path}: {e}") from e

    return MarkdownDocument(
        frontmatter=frontmatter, content=content, raw_content=raw_content
    )


def parse_markdown_string(content: str) -> MarkdownDocument:
    """Parse a markdown string with YAML frontmatter.

    Args:
        content: Markdown content string

    Returns:
        MarkdownDocument with parsed frontmatter and content
    """
    # Check if content has frontmatter
    if not content.startswith("---"):
        return MarkdownDocument(
            frontmatter={}, content=content.strip(), raw_content=content
        )

    # Split frontmatter and content
    parts = content.split("---", 2)

    if len(parts) < 3:
        return MarkdownDocument(
            frontmatter={}, content=content.strip(), raw_content=content
        )

    frontmatter_text = parts[1].strip()
    markdown_content = parts[2].strip()

    # Parse YAML frontmatter
    frontmatter = yaml.safe_load(frontmatter_text) or {}

    return MarkdownDocument(
        frontmatter=frontmatter, content=markdown_content, raw_content=content
    )
