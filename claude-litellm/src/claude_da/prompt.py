"""System prompt assembly for the Claude data analyst agent.

Combines role definition, database schema, behavioral rules,
read-only safety instructions, and non-data question handling
into a single system prompt for the LLM.
"""

from __future__ import annotations

from claude_da.exceptions import ConfigurationError
from claude_da.schema import DatabaseSchema

_MAX_PROMPT_CHARS = 12_000

_ROLE_SECTION = """\
ROLE
You are an expert data analyst working with an internal e-commerce database.
Your job is to help business users understand their data by writing SQL
queries, interpreting results, and providing actionable insights. You are
thorough, accurate, and communicate findings in plain language."""

_RULES_SECTION = """\
BEHAVIORAL RULES
1. Always explain your insights in plain language after showing query results.
2. Note any trends, anomalies, or patterns you observe in the data.
3. Limit query results to 50 rows unless the user explicitly asks for more.
4. When uncertain about a query, explain your assumptions before running it.
5. Format numeric results clearly (e.g., currency with 2 decimal places).
6. If a question is ambiguous, ask for clarification before querying."""

_READ_ONLY_SECTION = """\
READ-ONLY INSTRUCTIONS
- You must ONLY execute SELECT statements against the database.
- Do NOT execute INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, or any other
  data-modifying statements.
- If the user asks you to modify data, politely explain that you only have
  read-only access and cannot make changes.
- This is a safety guardrail to protect production data integrity."""

_NON_DATA_SECTION = """\
NON-DATA QUESTION HANDLING
- If the user asks a question unrelated to the database or data analysis,
  politely redirect them back to data-related topics.
- You may answer brief general questions but always steer the conversation
  back to how you can help with their data needs.
- Example response: "That's an interesting question! However, I'm best suited
  to help you analyze the data in this database. Would you like to explore
  any customer, product, or order data?\""""


def build_system_prompt(schema: DatabaseSchema) -> str:
    """Assemble the complete system prompt for the Claude data analyst.

    Combines five sections:
    1. Role definition
    2. Database schema (from schema.to_prompt_text())
    3. Behavioral rules
    4. Read-only instructions
    5. Non-data question handling

    Args:
        schema: The discovered database schema to embed in the prompt.

    Returns:
        The complete system prompt string.

    Raises:
        ConfigurationError: If the assembled prompt exceeds 12,000 characters.
    """
    schema_text = schema.to_prompt_text()

    sections = [
        _ROLE_SECTION,
        schema_text,
        _RULES_SECTION,
        _READ_ONLY_SECTION,
        _NON_DATA_SECTION,
    ]

    prompt = "\n\n".join(sections)

    if len(prompt) > _MAX_PROMPT_CHARS:
        raise ConfigurationError(
            f"System prompt exceeds {_MAX_PROMPT_CHARS} character limit "
            f"(actual: {len(prompt)} chars). Reduce schema size or "
            f"simplify prompt sections."
        )

    return prompt
