"""Database schema discovery and validation.

Provides dataclasses representing database structure and functions to
introspect a SQLite database, verify it is read-only, and render the
schema as human-readable text for LLM consumption.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from claude_da.exceptions import ConfigurationError

# --- Schema dataclasses ----------------------------------------------------


@dataclass
class ColumnInfo:
    """Metadata for a single database column.

    Attributes:
        name: Column name.
        type: SQL data type (e.g. "TEXT", "INTEGER").
        nullable: True if the column allows NULL values.
        primary_key: True if the column is (part of) the primary key.
    """

    name: str
    type: str
    nullable: bool
    primary_key: bool


@dataclass
class ForeignKey:
    """A foreign key relationship from one table to another.

    Attributes:
        from_column: Column name in the source table.
        to_table: Referenced table name.
        to_column: Referenced column name.
    """

    from_column: str
    to_table: str
    to_column: str


@dataclass
class TableSchema:
    """Schema for a single database table.

    Attributes:
        name: Table name.
        columns: Ordered list of column definitions.
        foreign_keys: Foreign key constraints on this table.
    """

    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)


@dataclass
class DatabaseSchema:
    """Complete schema for a database, containing all tables.

    Attributes:
        tables: List of table schemas in the database.
    """

    tables: list[TableSchema] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Render the schema as human-readable text for LLM consumption.

        Returns a formatted string showing all tables, their columns
        (with type, PK, nullable info), and foreign key relationships.

        Returns:
            Multi-line schema description under 8K chars for typical schemas.
        """
        lines: list[str] = []
        lines.append("DATABASE SCHEMA")
        lines.append("=" * 50)

        for table in self.tables:
            lines.append("")
            lines.append(f"Table: {table.name}")
            lines.append("-" * (len(table.name) + 7))
            lines.append("Columns:")

            for col in table.columns:
                flags: list[str] = []
                if col.primary_key:
                    flags.append("PK")
                if not col.nullable:
                    flags.append("NOT NULL")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                lines.append(f"  - {col.name} ({col.type}){flag_str}")

            if table.foreign_keys:
                lines.append("Foreign Keys:")
                for fk in table.foreign_keys:
                    lines.append(
                        f"  - {fk.from_column} -> {fk.to_table}.{fk.to_column}"
                    )

        lines.append("")
        return "\n".join(lines)


# --- Schema discovery ------------------------------------------------------


def discover_schema(db_path: str) -> DatabaseSchema:
    """Introspect a SQLite database and return its schema.

    Opens the database in read-only mode, queries sqlite_master for
    table names, and uses PRAGMA statements to discover columns and
    foreign keys.

    Args:
        db_path: Filesystem path to the SQLite database.

    Returns:
        A DatabaseSchema describing all user tables in the database.

    Raises:
        ConfigurationError: If the database cannot be opened or
            contains no user tables.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        raise ConfigurationError(f"Cannot open database at '{db_path}': {exc}") from exc

    try:
        # Get user table names (skip SQLite internals)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        if not table_names:
            raise ConfigurationError(f"Database at '{db_path}' contains no user tables")

        tables: list[TableSchema] = []
        for table_name in table_names:
            columns = _discover_columns(conn, table_name)
            foreign_keys = _discover_foreign_keys(conn, table_name)
            tables.append(
                TableSchema(
                    name=table_name,
                    columns=columns,
                    foreign_keys=foreign_keys,
                )
            )

        return DatabaseSchema(tables=tables)
    finally:
        conn.close()


def _discover_columns(conn: sqlite3.Connection, table_name: str) -> list[ColumnInfo]:
    """Read column metadata for a table via PRAGMA table_info.

    Returns:
        Ordered list of ColumnInfo for the table.
    """
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns: list[ColumnInfo] = []
    for row in cursor.fetchall():
        # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
        columns.append(
            ColumnInfo(
                name=row[1],
                type=row[2] if row[2] else "TEXT",
                nullable=not bool(row[3]),
                primary_key=bool(row[5]),
            )
        )
    return columns


def _discover_foreign_keys(
    conn: sqlite3.Connection, table_name: str
) -> list[ForeignKey]:
    """Read foreign key metadata for a table via PRAGMA foreign_key_list.

    Returns:
        List of ForeignKey relationships for the table.
    """
    cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
    foreign_keys: list[ForeignKey] = []
    for row in cursor.fetchall():
        # PRAGMA foreign_key_list returns:
        # id, seq, table, from, to, on_update, on_delete, match
        foreign_keys.append(
            ForeignKey(
                from_column=row[3],
                to_table=row[2],
                to_column=row[4],
            )
        )
    return foreign_keys


# --- Read-only verification ------------------------------------------------


def verify_read_only(db_path: str) -> None:
    """Verify that a database file is not writable.

    Attempts to create a temporary table. If the write succeeds, the
    database is writable and the function raises ConfigurationError.
    If the write fails (the expected case for a read-only file), the
    function returns silently.

    Args:
        db_path: Filesystem path to the SQLite database.

    Raises:
        ConfigurationError: If the database is writable.
    """
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.OperationalError:
        # Cannot open at all -- that is fine for our purposes
        return

    try:
        conn.execute("CREATE TABLE _claude_da_write_check (id INTEGER)")
        # If we get here, write succeeded -- database is writable
        conn.execute("DROP TABLE _claude_da_write_check")
        conn.close()
        raise ConfigurationError("Database is not read-only. Refusing to start.")
    except sqlite3.OperationalError:
        # Write failed as expected -- database is read-only
        conn.close()
        return
