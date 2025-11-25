"""
Utility functions for CollabSims.

This module provides helper functions used across the application.
"""

import re


def truncate_session_name(text: str, max_length: int = 30) -> str:
    """
    Truncate text at word/punctuation boundary, avoiding breaking words.

    Tries to stay close to max_length characters but will cut at spaces or
    punctuation marks instead of breaking words. If the text is shorter than
    max_length, returns it as-is.

    Args:
        text: The text to truncate
        max_length: Target maximum length (default 30)

    Returns:
        Truncated text, cut at a word/punctuation boundary
    """
    if not text:
        return text if text is None else ""
    if len(text) <= max_length:
        return text.strip()

    # Pattern for spaces and punctuation
    punctuation_pattern = r'[\s.,!?;:\'"()\[\]{}\-–—]'

    # Look backward from max_length to find a space or punctuation
    for i in range(max_length, -1, -1):
        if re.search(punctuation_pattern, text[i]):
            return text[:i].strip()

    # If no punctuation found, return up to max_length
    return text[:max_length].strip()
