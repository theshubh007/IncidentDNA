"""Shared sanitization utilities for IncidentDNA."""


def sanitize_sql_value(value: str) -> str:
    """Sanitize a value for safe SQL interpolation in LLM prompts.

    Strips dangerous SQL characters and truncates to 100 chars.
    Used in agent task descriptions where parameterized queries
    are not possible (prompt template strings).
    """
    if not isinstance(value, str):
        value = str(value)
    return value.replace("'", "").replace("\"", "").replace(";", "").replace("--", "").strip()[:100]
