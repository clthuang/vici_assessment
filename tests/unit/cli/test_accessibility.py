"""Tests for accessibility module."""

from questionary import Style

from subterminator.cli.accessibility import (
    get_questionary_style,
    should_use_animations,
    should_use_colors,
)


def test_should_use_colors_default(monkeypatch):
    """True when no env vars set"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    assert should_use_colors() is True


def test_should_use_colors_no_color_set(monkeypatch):
    """False when NO_COLOR is set (any value)"""
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_use_colors() is False
    monkeypatch.setenv("NO_COLOR", "")
    assert should_use_colors() is False


def test_should_use_colors_term_dumb(monkeypatch):
    """False when TERM=dumb"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert should_use_colors() is False


def test_should_use_animations_default(monkeypatch):
    """True when no env vars set"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("SUBTERMINATOR_PLAIN", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    assert should_use_animations() is True


def test_should_use_animations_no_color(monkeypatch):
    """False when NO_COLOR set (inherits from colors)"""
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_use_animations() is False


def test_should_use_animations_plain_set(monkeypatch):
    """False when SUBTERMINATOR_PLAIN set"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("SUBTERMINATOR_PLAIN", "1")
    assert should_use_animations() is False


def test_get_questionary_style_with_colors(monkeypatch):
    """Returns Style object when colors enabled"""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TERM", raising=False)
    style = get_questionary_style()
    assert style is not None
    assert isinstance(style, Style)


def test_get_questionary_style_no_colors(monkeypatch):
    """Returns None when colors disabled"""
    monkeypatch.setenv("NO_COLOR", "1")
    assert get_questionary_style() is None
