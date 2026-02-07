"""Unit tests for Claude-DA system prompt assembly.

Verifies that the system prompt contains all required sections,
respects the character limit, and raises on oversized schemas.
"""

from __future__ import annotations

import pytest

from claude_da.exceptions import ConfigurationError
from claude_da.prompt import build_system_prompt
from claude_da.schema import (
    ColumnInfo,
    DatabaseSchema,
    ForeignKey,
    TableSchema,
)

# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def demo_schema() -> DatabaseSchema:
    """A realistic 4-table e-commerce schema for prompt testing."""
    return DatabaseSchema(
        tables=[
            TableSchema(
                name="customers",
                columns=[
                    ColumnInfo("id", "INTEGER", False, True),
                    ColumnInfo("name", "TEXT", False, False),
                    ColumnInfo("email", "TEXT", False, False),
                    ColumnInfo("tier", "TEXT", False, False),
                    ColumnInfo("created_at", "TEXT", False, False),
                ],
                foreign_keys=[],
            ),
            TableSchema(
                name="products",
                columns=[
                    ColumnInfo("id", "INTEGER", False, True),
                    ColumnInfo("name", "TEXT", False, False),
                    ColumnInfo("category", "TEXT", False, False),
                    ColumnInfo("price", "REAL", False, False),
                ],
                foreign_keys=[],
            ),
            TableSchema(
                name="orders",
                columns=[
                    ColumnInfo("id", "INTEGER", False, True),
                    ColumnInfo("customer_id", "INTEGER", False, False),
                    ColumnInfo("status", "TEXT", False, False),
                    ColumnInfo("created_at", "TEXT", False, False),
                ],
                foreign_keys=[
                    ForeignKey("customer_id", "customers", "id"),
                ],
            ),
            TableSchema(
                name="order_items",
                columns=[
                    ColumnInfo("id", "INTEGER", False, True),
                    ColumnInfo("order_id", "INTEGER", False, False),
                    ColumnInfo("product_id", "INTEGER", False, False),
                    ColumnInfo("quantity", "INTEGER", False, False),
                    ColumnInfo("unit_price", "REAL", False, False),
                ],
                foreign_keys=[
                    ForeignKey("order_id", "orders", "id"),
                    ForeignKey("product_id", "products", "id"),
                ],
            ),
        ]
    )


# --- Tests ------------------------------------------------------------------


class TestPromptSections:
    """The system prompt contains all five required sections."""

    def test_contains_role_definition(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert "ROLE" in prompt
        assert "data analyst" in prompt

    def test_contains_schema_text(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert "DATABASE SCHEMA" in prompt
        assert "customers" in prompt
        assert "products" in prompt
        assert "orders" in prompt
        assert "order_items" in prompt

    def test_contains_behavioral_rules(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert "BEHAVIORAL RULES" in prompt
        assert "insights" in prompt
        assert "trends" in prompt
        assert "50 rows" in prompt

    def test_contains_read_only_instructions(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert "READ-ONLY" in prompt
        assert "SELECT" in prompt

    def test_contains_non_data_handling(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert "NON-DATA" in prompt
        assert "redirect" in prompt


class TestPromptSize:
    """System prompt respects the 12K character limit."""

    def test_under_12k_chars(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert len(prompt) < 12_000, f"Prompt is {len(prompt)} chars, expected < 12,000"

    def test_prompt_is_nonempty(self, demo_schema: DatabaseSchema) -> None:
        prompt = build_system_prompt(demo_schema)
        assert len(prompt) > 100


class TestOversizedSchema:
    """build_system_prompt raises ConfigurationError on oversized schemas."""

    def test_raises_on_huge_schema(self) -> None:
        """Create a schema large enough to blow the 12K limit."""
        # Each table with many columns adds significant text
        huge_tables = []
        for i in range(100):
            columns = [
                ColumnInfo(
                    name=f"column_{j}_with_a_very_long_name_for_testing",
                    type="TEXT",
                    nullable=True,
                    primary_key=False,
                )
                for j in range(20)
            ]
            huge_tables.append(
                TableSchema(
                    name=f"table_{i}_with_a_very_long_name_for_testing",
                    columns=columns,
                    foreign_keys=[],
                )
            )

        huge_schema = DatabaseSchema(tables=huge_tables)

        with pytest.raises(ConfigurationError, match="exceeds"):
            build_system_prompt(huge_schema)
