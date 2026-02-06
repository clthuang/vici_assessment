"""Snapshot parsing for Playwright MCP output.

This module provides functions to parse the markdown-formatted output
from Playwright MCP's browser_snapshot tool into structured data.

Playwright MCP returns text in this format:
    ### Page
    - Page URL: https://example.com
    - Page Title: Example Domain
    - generic [ref=s1e0]:
      - banner [ref=s1e1]:
      ...

Note: Older versions may include "- Page Snapshot:" marker before content.
"""

from __future__ import annotations

import re

from .exceptions import SnapshotValidationError
from .types import NormalizedSnapshot

# Regex patterns for extracting data from Playwright MCP output
URL_PATTERN = re.compile(r"- Page URL: (.+)")
TITLE_PATTERN = re.compile(r"- Page Title:(.*)")


def normalize_snapshot(text: str) -> NormalizedSnapshot:
    """Parse Playwright MCP browser_snapshot output into structured data.

    Args:
        text: Raw text output from browser_snapshot tool.

    Returns:
        NormalizedSnapshot with extracted url, title, and content.

    Raises:
        SnapshotValidationError: If required fields cannot be extracted.
    """
    if not text:
        raise SnapshotValidationError(
            "Empty snapshot text received. Expected Playwright MCP output."
        )

    # Extract URL
    url_match = URL_PATTERN.search(text)
    if not url_match:
        raise SnapshotValidationError(
            f"Could not find Page URL line. Input starts with: {text[:200]}"
        )
    url = url_match.group(1).strip()

    # Extract title
    title_match = TITLE_PATTERN.search(text)
    if not title_match:
        raise SnapshotValidationError(
            f"Could not find Page Title line. Input starts with: {text[:200]}"
        )
    title = title_match.group(1).strip()

    # Extract content: everything after the title line
    # Modern Playwright MCP format has content directly after title line
    # Older format may include "- Page Snapshot:" marker
    title_end = title_match.end()
    content = text[title_end:].strip()

    # Strip optional "- Page Snapshot:" prefix if present (backwards compat)
    snapshot_marker = "- Page Snapshot:"
    if content.startswith(snapshot_marker):
        content = content[len(snapshot_marker) :].strip()

    return NormalizedSnapshot(
        url=url,
        title=title,
        content=content,
    )
