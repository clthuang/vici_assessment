"""Tests for snapshot parsing."""

import pytest

from subterminator.mcp_orchestrator.exceptions import SnapshotValidationError
from subterminator.mcp_orchestrator.snapshot import normalize_snapshot
from subterminator.mcp_orchestrator.types import NormalizedSnapshot


class TestNormalizeSnapshot:
    """Tests for normalize_snapshot function."""

    def test_parses_valid_snapshot(self):
        """normalize_snapshot extracts url, title, content from valid input."""
        text = """### Page state
- Page URL: https://example.com
- Page Title: Example Domain
- Page Snapshot:
```yaml
- document [ref=@e0]:
  - heading "Example Domain" [ref=@e1]
```"""
        result = normalize_snapshot(text)

        assert isinstance(result, NormalizedSnapshot)
        assert result.url == "https://example.com"
        assert result.title == "Example Domain"
        assert "document [ref=@e0]" in result.content
        assert result.screenshot_path is None

    def test_handles_complex_url(self):
        """normalize_snapshot handles URLs with query params."""
        text = """### Page state
- Page URL: https://netflix.com/login?locale=en-US&nextpage=browse
- Page Title: Sign In - Netflix
- Page Snapshot:
content here"""
        result = normalize_snapshot(text)

        assert result.url == "https://netflix.com/login?locale=en-US&nextpage=browse"
        assert result.title == "Sign In - Netflix"

    def test_handles_empty_title(self):
        """normalize_snapshot handles empty but present title."""
        text = """### Page state
- Page URL: about:blank
- Page Title:
- Page Snapshot:
minimal"""
        result = normalize_snapshot(text)

        assert result.url == "about:blank"
        assert result.title == ""
        assert result.content == "minimal"

    def test_raises_on_empty_input(self):
        """normalize_snapshot raises SnapshotValidationError on empty input."""
        with pytest.raises(SnapshotValidationError) as exc_info:
            normalize_snapshot("")
        assert "Empty snapshot text" in str(exc_info.value)

    def test_raises_on_missing_url(self):
        """normalize_snapshot raises when Page URL line is missing."""
        text = """### Page state
- Page Title: Example
- Page Snapshot:
content"""
        with pytest.raises(SnapshotValidationError) as exc_info:
            normalize_snapshot(text)
        assert "Could not find Page URL line" in str(exc_info.value)
        # Error message should include input preview
        assert "Page state" in str(exc_info.value)

    def test_raises_on_missing_title(self):
        """normalize_snapshot raises when Page Title line is missing."""
        text = """### Page state
- Page URL: https://example.com
- Page Snapshot:
content"""
        with pytest.raises(SnapshotValidationError) as exc_info:
            normalize_snapshot(text)
        assert "Could not find Page Title line" in str(exc_info.value)

    def test_handles_no_content_after_title(self):
        """normalize_snapshot returns empty content when nothing follows title."""
        text = """### Page state
- Page URL: https://example.com
- Page Title: Example"""
        result = normalize_snapshot(text)

        assert result.url == "https://example.com"
        assert result.title == "Example"
        assert result.content == ""

    def test_handles_multiline_content(self):
        """normalize_snapshot extracts multi-line content correctly."""
        text = """### Page state
- Page URL: https://example.com
- Page Title: Example
- Page Snapshot:
```yaml
- document [ref=@e0]:
  - navigation [ref=@e1]:
    - link "Home" [ref=@e2]
    - link "About" [ref=@e3]
  - main [ref=@e4]:
    - heading "Welcome" [ref=@e5]
    - paragraph [ref=@e6]:
      - text "Hello world"
```"""
        result = normalize_snapshot(text)

        assert "document [ref=@e0]" in result.content
        assert 'link "Home"' in result.content
        assert 'heading "Welcome"' in result.content

    def test_handles_special_characters_in_content(self):
        """normalize_snapshot handles special chars in content."""
        text = """### Page state
- Page URL: https://example.com
- Page Title: Test <script>alert('xss')</script>
- Page Snapshot:
- button "Click & Save" [ref=@e1]
- text "Price: $19.99 (50% off!)"
"""
        result = normalize_snapshot(text)

        assert "Click & Save" in result.content
        assert "$19.99" in result.content
        # Title should be preserved as-is
        assert "<script>" in result.title


class TestNormalizeSnapshotFixtures:
    """Tests using realistic fixtures."""

    # Modern format: No "- Page Snapshot:" marker, content directly after title
    MODERN_FORMAT_FIXTURE = """### Page
- Page URL: https://www.netflix.com/browse
- Page Title: Netflix
- generic [ref=s1e0]:
  - banner [ref=s1e1]:
    - img "Netflix" [ref=s1e2]
  - navigation [ref=s1e3]:
    - link "Home" [ref=s1e4]
    - link "TV Shows" [ref=s1e5]
  - main [ref=s1e6]:
    - heading "Popular on Netflix" [ref=s1e7]"""

    # Legacy format: With "- Page Snapshot:" marker
    EXAMPLE_COM_FIXTURE = """### Page state
- Page URL: https://example.com/
- Page Title: Example Domain
- Page Snapshot:
```yaml
- document [ref=@e0]:
  - banner [ref=@e1]:
  - heading "Example Domain" [level=1] [ref=@e2]
  - paragraph [ref=@e3]:
    - text "This domain is for use in illustrative examples in documents."
  - paragraph [ref=@e4]:
    - link "More information..." [ref=@e5]
```"""

    NETFLIX_LOGIN_FIXTURE = """### Page state
- Page URL: https://www.netflix.com/login
- Page Title: Sign In - Netflix
- Page Snapshot:
```yaml
- document [ref=@e0]:
  - banner [ref=@e1]:
    - img "Netflix" [ref=@e2]
  - main [ref=@e3]:
    - heading "Sign In" [level=1] [ref=@e4]
    - form [ref=@e5]:
      - textbox "Email or phone number" [ref=@e6]
      - textbox "Password" [ref=@e7]
      - button "Sign In" [ref=@e8]
      - checkbox "Remember me" [ref=@e9]
    - link "Forgot password?" [ref=@e10]
    - text "New to Netflix?"
    - link "Sign up now" [ref=@e11]
```"""

    def test_parses_modern_format_fixture(self):
        """normalize_snapshot parses modern Playwright MCP format (no marker)."""
        result = normalize_snapshot(self.MODERN_FORMAT_FIXTURE)

        assert result.url == "https://www.netflix.com/browse"
        assert result.title == "Netflix"
        assert "generic [ref=s1e0]" in result.content
        assert "Popular on Netflix" in result.content

    def test_parses_example_com_fixture(self):
        """normalize_snapshot parses example.com fixture."""
        result = normalize_snapshot(self.EXAMPLE_COM_FIXTURE)

        assert result.url == "https://example.com/"
        assert result.title == "Example Domain"
        assert "Example Domain" in result.content
        assert "More information" in result.content

    def test_parses_netflix_login_fixture(self):
        """normalize_snapshot parses Netflix login fixture."""
        result = normalize_snapshot(self.NETFLIX_LOGIN_FIXTURE)

        assert result.url == "https://www.netflix.com/login"
        assert result.title == "Sign In - Netflix"
        assert "Sign In" in result.content
        assert "Email or phone number" in result.content
        assert "Password" in result.content
        assert "Forgot password" in result.content
