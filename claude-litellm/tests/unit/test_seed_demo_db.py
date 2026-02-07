"""Unit tests for the demo database seeder script.

Verifies idempotency, data counts, date distribution, and
read-only file permissions.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

# Add scripts/ to import path so we can import the seeder directly
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import pytest  # noqa: E402
from seed_demo_db import seed_database  # noqa: E402


class TestSeederIdempotency:
    """Running the seeder twice produces a valid database without errors."""

    def test_run_twice_no_error(self, tmp_path: Path) -> None:
        db_path = tmp_path / "demo.db"

        # First run
        result1 = seed_database(db_path)
        assert result1.exists()

        # Second run -- should not raise
        result2 = seed_database(db_path)
        assert result2.exists()

    def test_second_run_produces_same_counts(self, tmp_path: Path) -> None:
        db_path = tmp_path / "demo.db"

        seed_database(db_path)
        counts_1 = _get_row_counts(db_path)

        seed_database(db_path)
        counts_2 = _get_row_counts(db_path)

        assert counts_1 == counts_2


class TestFilePermissions:
    """Output file must be read-only after seeding."""

    def test_output_is_read_only(self, tmp_path: Path) -> None:
        db_path = tmp_path / "demo.db"
        seed_database(db_path)
        assert not os.access(str(db_path), os.W_OK)

    def test_output_is_readable(self, tmp_path: Path) -> None:
        db_path = tmp_path / "demo.db"
        seed_database(db_path)
        assert os.access(str(db_path), os.R_OK)


class TestDataCounts:
    """Seeded database contains minimum required row counts."""

    @pytest.fixture(autouse=True)
    def _seed(self, tmp_path: Path) -> None:
        self.db_path = tmp_path / "demo.db"
        seed_database(self.db_path)
        self.counts = _get_row_counts(self.db_path)

    def test_customers_count(self) -> None:
        assert self.counts["customers"] >= 50

    def test_products_count(self) -> None:
        assert self.counts["products"] >= 20

    def test_orders_count(self) -> None:
        assert self.counts["orders"] >= 200

    def test_order_items_count(self) -> None:
        assert self.counts["order_items"] >= 500


class TestDateDistribution:
    """Orders span at least 6 distinct calendar months."""

    def test_orders_span_six_or_more_months(self, tmp_path: Path) -> None:
        db_path = tmp_path / "demo.db"
        seed_database(db_path)

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT DISTINCT substr(created_at, 1, 7) FROM orders"
        ).fetchall()
        conn.close()

        distinct_months = len(rows)
        assert distinct_months >= 6, (
            f"Expected 6+ months, got {distinct_months}: {[r[0] for r in rows]}"
        )


class TestSchemaStructure:
    """Seeded database has the expected 4 tables with proper schema."""

    def test_has_four_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "demo.db"
        seed_database(db_path)

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()

        table_names = [t[0] for t in tables]
        assert "customers" in table_names
        assert "products" in table_names
        assert "orders" in table_names
        assert "order_items" in table_names


# --- Helpers ---------------------------------------------------------------


def _get_row_counts(db_path: Path) -> dict[str, int]:
    """Return a dict of table_name -> row_count."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    counts = {}
    for table in ["customers", "products", "orders", "order_items"]:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        counts[table] = row[0]
    conn.close()
    return counts
