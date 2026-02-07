"""Unit tests for Claude-DA schema discovery and validation.

Uses a temporary SQLite database with the 4-table e-commerce schema
(independent of the seeder script) to test discover_schema,
to_prompt_text, and verify_read_only.
"""

from __future__ import annotations

import sqlite3
import stat
from pathlib import Path

import pytest

from claude_da.exceptions import ConfigurationError
from claude_da.schema import (
    ColumnInfo,
    DatabaseSchema,
    ForeignKey,
    TableSchema,
    discover_schema,
    verify_read_only,
)

# --- Fixtures ---------------------------------------------------------------

_SCHEMA_DDL = """\
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    tier TEXT NOT NULL CHECK(tier IN ('free', 'pro', 'enterprise')),
    created_at TEXT NOT NULL
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    status TEXT NOT NULL CHECK(
        status IN ('pending', 'completed', 'cancelled', 'refunded')
    ),
    created_at TEXT NOT NULL
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
"""

_SEED_SQL = """\
INSERT INTO customers VALUES (
    1, 'Alice', 'alice@test.com', 'pro', '2024-01-15T10:00:00'
);
INSERT INTO products VALUES (1, 'Widget', 'Gadgets', 9.99);
INSERT INTO orders VALUES (1, 1, 'completed', '2024-02-01T12:00:00');
INSERT INTO order_items VALUES (1, 1, 1, 2, 9.99);
"""


@pytest.fixture
def demo_db(tmp_path: Path) -> Path:
    """Create a temp DB with the 4-table schema and a few rows."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA_DDL)
    conn.executescript(_SEED_SQL)
    conn.close()
    return db_path


@pytest.fixture
def readonly_db(demo_db: Path) -> Path:
    """Return a read-only (chmod 444) version of the demo DB."""
    demo_db.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return demo_db


# --- Tests for discover_schema ---------------------------------------------


class TestDiscoverSchema:
    """discover_schema correctly introspects the database structure."""

    def test_finds_four_tables(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        table_names = sorted(t.name for t in schema.tables)
        assert table_names == [
            "customers", "order_items", "orders", "products"
        ]

    def test_customers_columns(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        customers = _find_table(schema, "customers")
        col_names = [c.name for c in customers.columns]
        assert col_names == ["id", "name", "email", "tier", "created_at"]

    def test_customers_id_is_pk(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        customers = _find_table(schema, "customers")
        id_col = customers.columns[0]
        assert id_col.primary_key is True

    def test_customers_name_not_nullable(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        customers = _find_table(schema, "customers")
        name_col = customers.columns[1]
        assert name_col.nullable is False

    def test_column_types(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        products = _find_table(schema, "products")
        type_map = {c.name: c.type for c in products.columns}
        assert type_map["id"] == "INTEGER"
        assert type_map["name"] == "TEXT"
        assert type_map["price"] == "REAL"

    def test_foreign_keys_on_orders(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        orders = _find_table(schema, "orders")
        assert len(orders.foreign_keys) == 1
        fk = orders.foreign_keys[0]
        assert fk.from_column == "customer_id"
        assert fk.to_table == "customers"
        assert fk.to_column == "id"

    def test_foreign_keys_on_order_items(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        order_items = _find_table(schema, "order_items")
        assert len(order_items.foreign_keys) == 2
        fk_tables = {fk.to_table for fk in order_items.foreign_keys}
        assert fk_tables == {"orders", "products"}

    def test_raises_on_nonexistent_file(self) -> None:
        with pytest.raises(ConfigurationError, match="Cannot open"):
            discover_schema("/nonexistent/path/to/db.sqlite")

    def test_raises_on_empty_database(self, tmp_path: Path) -> None:
        empty_db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(empty_db))
        conn.close()
        with pytest.raises(ConfigurationError, match="no user tables"):
            discover_schema(str(empty_db))


# --- Tests for to_prompt_text -----------------------------------------------


class TestToPromptText:
    """DatabaseSchema.to_prompt_text() produces readable schema text."""

    def test_contains_all_table_names(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        text = schema.to_prompt_text()
        for name in ["customers", "products", "orders", "order_items"]:
            assert name in text

    def test_contains_column_names(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        text = schema.to_prompt_text()
        for col_name in ["email", "category", "price", "quantity", "unit_price"]:
            assert col_name in text

    def test_contains_foreign_key_info(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        text = schema.to_prompt_text()
        assert "customer_id -> customers.id" in text
        assert "order_id -> orders.id" in text
        assert "product_id -> products.id" in text

    def test_under_8k_chars(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        text = schema.to_prompt_text()
        assert len(text) < 8000, f"Prompt text is {len(text)} chars, expected < 8000"

    def test_shows_pk_and_not_null_flags(self, demo_db: Path) -> None:
        schema = discover_schema(str(demo_db))
        text = schema.to_prompt_text()
        assert "PK" in text
        assert "NOT NULL" in text


# --- Tests for verify_read_only --------------------------------------------


class TestVerifyReadOnly:
    """verify_read_only raises on writable DBs, passes on read-only."""

    def test_passes_on_readonly_file(self, readonly_db: Path) -> None:
        # Should return silently
        verify_read_only(str(readonly_db))

    def test_raises_on_writable_file(self, demo_db: Path) -> None:
        # demo_db is writable by default
        with pytest.raises(
            ConfigurationError, match="not read-only"
        ):
            verify_read_only(str(demo_db))


# --- Tests for dataclass construction --------------------------------------


class TestDataclasses:
    """Schema dataclasses can be constructed and have expected fields."""

    def test_column_info_fields(self) -> None:
        col = ColumnInfo(name="id", type="INTEGER", nullable=False, primary_key=True)
        assert col.name == "id"
        assert col.type == "INTEGER"
        assert col.nullable is False
        assert col.primary_key is True

    def test_foreign_key_fields(self) -> None:
        fk = ForeignKey(from_column="user_id", to_table="users", to_column="id")
        assert fk.from_column == "user_id"
        assert fk.to_table == "users"
        assert fk.to_column == "id"

    def test_table_schema_defaults(self) -> None:
        ts = TableSchema(name="test")
        assert ts.columns == []
        assert ts.foreign_keys == []

    def test_database_schema_defaults(self) -> None:
        ds = DatabaseSchema()
        assert ds.tables == []


# --- Helpers ---------------------------------------------------------------


def _find_table(schema: DatabaseSchema, name: str) -> TableSchema:
    """Find a table by name in the schema, or fail the test."""
    for table in schema.tables:
        if table.name == name:
            return table
    pytest.fail(f"Table '{name}' not found in schema")
