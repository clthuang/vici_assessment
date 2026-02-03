"""Tests for the __main__ module entry point."""

import subprocess
import sys


def test_module_entry_point_help():
    """Test that running as module with --help works."""
    result = subprocess.run(
        [sys.executable, "-m", "subterminator", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "subterminator" in result.stdout.lower() or "cancel" in result.stdout.lower()


def test_module_imports():
    """Test that __main__ module can be imported."""
    import subterminator.__main__
    assert hasattr(subterminator.__main__, "app")
