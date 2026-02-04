"""Tests for SelectorConfig dataclass."""

import pytest

from subterminator.services.selectors import SelectorConfig


class TestSelectorConfig:
    """Tests for the SelectorConfig dataclass."""

    def test_create_with_css_only(self) -> None:
        """SelectorConfig should create with css list only."""
        config = SelectorConfig(css=["#my-selector"])
        assert config.css == ["#my-selector"]
        assert config.aria is None

    def test_create_with_css_and_aria(self) -> None:
        """SelectorConfig should create with css and aria tuple."""
        config = SelectorConfig(css=["#selector"], aria=("button", "Name"))
        assert config.css == ["#selector"]
        assert config.aria == ("button", "Name")

    def test_create_with_multiple_css_selectors(self) -> None:
        """SelectorConfig should allow multiple CSS selectors."""
        config = SelectorConfig(css=["#first", ".second", "[data-test='third']"])
        assert len(config.css) == 3
        assert config.css[0] == "#first"
        assert config.css[1] == ".second"
        assert config.css[2] == "[data-test='third']"

    def test_empty_css_raises_value_error(self) -> None:
        """SelectorConfig with empty css list should raise ValueError."""
        with pytest.raises(ValueError, match="css list cannot be empty"):
            SelectorConfig(css=[])

    def test_empty_css_with_aria_raises_value_error(self) -> None:
        """SelectorConfig with empty css but valid aria should raise ValueError."""
        with pytest.raises(ValueError, match="css list cannot be empty"):
            SelectorConfig(css=[], aria=("button", "Submit"))

    def test_aria_is_optional(self) -> None:
        """aria parameter should be optional and default to None."""
        config = SelectorConfig(css=["selector"])
        assert config.aria is None

    def test_aria_role_and_name(self) -> None:
        """aria tuple should contain (role, name)."""
        config = SelectorConfig(css=["#btn"], aria=("button", "Click Me"))
        role, name = config.aria
        assert role == "button"
        assert name == "Click Me"

    def test_equality(self) -> None:
        """Two SelectorConfigs with same values should be equal."""
        config1 = SelectorConfig(css=["#a", "#b"], aria=("link", "Test"))
        config2 = SelectorConfig(css=["#a", "#b"], aria=("link", "Test"))
        assert config1 == config2

    def test_inequality(self) -> None:
        """Two SelectorConfigs with different values should not be equal."""
        config1 = SelectorConfig(css=["#a"])
        config2 = SelectorConfig(css=["#b"])
        assert config1 != config2
