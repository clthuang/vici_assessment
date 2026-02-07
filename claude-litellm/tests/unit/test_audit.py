"""Unit tests for Claude-DA audit logging.

Covers JSON serialization, stdout output, file (JSONL) output,
error handling, and verbose vs. summary modes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_da.audit import AuditEntry, AuditLogger, AuditMetadata


def _make_entry(
    *,
    user_question: str = "How many users?",
    sql_queries: list[str] | None = None,
    query_results: list[dict] | None = None,
    final_response: str = "There are 42 users.",
) -> AuditEntry:
    """Helper to construct a minimal AuditEntry for testing."""
    return AuditEntry(
        session_id="00000000-0000-4000-8000-000000000001",
        timestamp="2025-01-15T10:30:00Z",
        user_question=user_question,
        sql_queries_executed=sql_queries or ["SELECT COUNT(*) FROM users"],
        query_results_summary=query_results or [{"count": 42}],
        final_response=final_response,
        metadata=AuditMetadata(
            model="claude-sonnet-4-5-20250929",
            prompt_tokens=150,
            completion_tokens=50,
            cost_estimate_usd=0.002,
            duration_seconds=1.5,
            tool_call_count=1,
        ),
    )


class TestAuditEntrySerialization:
    """AuditEntry round-trips through JSON correctly."""

    def test_to_dict_returns_dict(self) -> None:
        entry = _make_entry()
        d = entry.to_dict()
        assert isinstance(d, dict)
        assert d["session_id"] == "00000000-0000-4000-8000-000000000001"
        assert d["metadata"]["model"] == "claude-sonnet-4-5-20250929"

    def test_json_round_trip(self) -> None:
        entry = _make_entry()
        json_str = json.dumps(entry.to_dict())
        restored = json.loads(json_str)
        assert restored["user_question"] == "How many users?"
        assert restored["sql_queries_executed"] == ["SELECT COUNT(*) FROM users"]
        assert restored["metadata"]["prompt_tokens"] == 150

    def test_to_dict_with_none_tokens(self) -> None:
        entry = _make_entry()
        entry.metadata.prompt_tokens = None
        entry.metadata.completion_tokens = None
        entry.metadata.cost_estimate_usd = None
        d = entry.to_dict()
        assert d["metadata"]["prompt_tokens"] is None


class TestAuditLoggerStdout:
    """AuditLogger with log_output='stdout' writes valid JSON to stdout."""

    @pytest.mark.asyncio
    async def test_stdout_output_is_valid_json(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        logger = AuditLogger(log_output="stdout", log_file="unused.jsonl")
        entry = _make_entry()
        await logger.log(entry)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["session_id"] == entry.session_id

    @pytest.mark.asyncio
    async def test_stdout_verbose_includes_results(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        logger = AuditLogger(log_output="stdout", log_file="unused.jsonl", verbose=True)
        entry = _make_entry(query_results=[{"id": 1, "name": "Alice"}])
        await logger.log(entry)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["query_results_summary"] == [{"id": 1, "name": "Alice"}]

    @pytest.mark.asyncio
    async def test_stdout_summary_omits_results(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        logger = AuditLogger(
            log_output="stdout", log_file="unused.jsonl", verbose=False
        )
        entry = _make_entry(query_results=[{"id": 1, "name": "Alice"}])
        await logger.log(entry)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "query_results_summary" not in parsed


class TestAuditLoggerFile:
    """AuditLogger with log_output='file' writes valid JSONL."""

    @pytest.mark.asyncio
    async def test_file_output_creates_valid_jsonl(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_output="file", log_file=str(log_file))
        entry = _make_entry()
        await logger.log(entry)

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["session_id"] == entry.session_id

    @pytest.mark.asyncio
    async def test_file_appends_multiple_entries(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_output="file", log_file=str(log_file))
        await logger.log(_make_entry(user_question="Q1"))
        await logger.log(_make_entry(user_question="Q2"))

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["user_question"] == "Q1"
        assert json.loads(lines[1])["user_question"] == "Q2"


class TestAuditLoggerBoth:
    """AuditLogger with log_output='both' writes to stdout and file."""

    @pytest.mark.asyncio
    async def test_both_outputs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_output="both", log_file=str(log_file))
        entry = _make_entry()
        await logger.log(entry)

        # Verify stdout
        captured = capsys.readouterr()
        stdout_parsed = json.loads(captured.out)
        assert stdout_parsed["session_id"] == entry.session_id

        # Verify file
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        file_parsed = json.loads(lines[0])
        assert file_parsed["session_id"] == entry.session_id


class TestAuditLoggerErrorHandling:
    """Write failures are caught and logged to stderr, never raised."""

    @pytest.mark.asyncio
    async def test_file_write_failure_logs_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        logger = AuditLogger(
            log_output="file",
            log_file="/nonexistent/dir/audit.jsonl",
        )
        entry = _make_entry()

        # Should not raise
        await logger.log(entry)

        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "Error" in captured.err

    @pytest.mark.asyncio
    async def test_stdout_write_failure_logs_to_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        logger = AuditLogger(log_output="stdout", log_file="unused.jsonl")
        entry = _make_entry()

        with patch("sys.stdout.write", side_effect=OSError("broken pipe")):
            # Should not raise
            await logger.log(entry)

        captured = capsys.readouterr()
        assert "error" in captured.err.lower() or "Error" in captured.err
