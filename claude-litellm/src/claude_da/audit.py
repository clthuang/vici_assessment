"""Claude-DA audit logging.

Provides structured audit entries and an async logger that writes
to stdout (JSON), file (JSONL), or both. All I/O errors are caught
internally and reported to stderr -- audit failures must never crash
the application.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass, field


@dataclass
class AuditMetadata:
    """Token usage, cost, and timing metadata for an agent turn.

    Attributes:
        model: The Claude model identifier used.
        prompt_tokens: Number of prompt tokens (None if unavailable).
        completion_tokens: Number of completion tokens (None if unavailable).
        cost_estimate_usd: Estimated cost in USD (None if unavailable).
        duration_seconds: Wall-clock seconds for the agent turn.
        tool_call_count: Number of tool calls made during the turn.
    """

    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_estimate_usd: float | None
    duration_seconds: float
    tool_call_count: int


@dataclass
class AuditEntry:
    """A single audit record for one user question/answer cycle.

    Attributes:
        session_id: UUID v4 identifying the session.
        timestamp: ISO 8601 timestamp.
        user_question: The user's natural-language question.
        sql_queries_executed: SQL queries the agent ran.
        query_results_summary: Summarized query results.
        final_response: The agent's final answer to the user.
        metadata: Token/cost/timing metadata.
    """

    session_id: str
    timestamp: str
    user_question: str
    sql_queries_executed: list[str] = field(default_factory=list)
    query_results_summary: list[dict] = field(default_factory=list)
    final_response: str = ""
    metadata: AuditMetadata = field(
        default_factory=lambda: AuditMetadata(
            model="unknown",
            prompt_tokens=None,
            completion_tokens=None,
            cost_estimate_usd=None,
            duration_seconds=0.0,
            tool_call_count=0,
        )
    )

    def to_dict(self) -> dict:
        """Convert to a plain dict suitable for JSON serialization.

        Returns:
            A dictionary representation of this audit entry.
        """
        return asdict(self)


class AuditLogger:
    """Async audit logger supporting stdout, file, and both modes.

    Args:
        log_output: Where to write logs ("stdout", "file", or "both").
        log_file: Path for JSONL file output.
        verbose: If True, include full query_results_summary in output.
            If False, omit query_results_summary for compact logs.
    """

    def __init__(
        self,
        log_output: str = "stdout",
        log_file: str = "./claude-da-audit.jsonl",
        verbose: bool = False,
    ) -> None:
        self._log_output = log_output
        self._log_file = log_file
        self._verbose = verbose

    async def log(self, entry: AuditEntry) -> None:
        """Write an audit entry to the configured output(s).

        All I/O errors are caught and reported to stderr. This method
        never raises exceptions to the caller.

        Args:
            entry: The audit entry to log.
        """
        data = entry.to_dict()

        if not self._verbose:
            data.pop("query_results_summary", None)

        if self._log_output in ("stdout", "both"):
            await self._write_stdout(data)

        if self._log_output in ("file", "both"):
            await self._write_file(data)

    async def _write_stdout(self, data: dict) -> None:
        """Write JSON to stdout, catching errors."""
        try:
            json_str = json.dumps(data, indent=2, default=str)
            sys.stdout.write(json_str + "\n")
            sys.stdout.flush()
        except Exception as exc:
            self._log_error(f"Error writing audit to stdout: {exc}")

    async def _write_file(self, data: dict) -> None:
        """Append a JSONL line to the log file via asyncio.to_thread."""
        try:
            json_line = json.dumps(data, default=str)
            await asyncio.to_thread(self._append_line, json_line)
        except Exception as exc:
            self._log_error(f"Error writing audit to file: {exc}")

    def _append_line(self, line: str) -> None:
        """Synchronous file append (run in a thread)."""
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def _log_error(message: str) -> None:
        """Write an error message to stderr."""
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
