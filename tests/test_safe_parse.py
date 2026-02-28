"""
Unit tests for _safe_parse and _safe_float helpers in manager.py.

These are pure Python — no Snowflake, no Composio, no network calls.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock

# Stub heavy external modules before importing manager
sys.modules.setdefault("snowflake", MagicMock())
sys.modules.setdefault("snowflake.connector", MagicMock())

# Stub dotenv
_dotenv_mock = MagicMock()
_dotenv_mock.load_dotenv = MagicMock(return_value=None)
sys.modules["dotenv"] = _dotenv_mock

# Stub utils submodules individually
_mock_conn = MagicMock()
_mock_conn.run_dml = MagicMock(return_value=None)
_mock_conn.run_query = MagicMock(return_value=[])
_mock_conn.get_connection = MagicMock(return_value=MagicMock())
sys.modules.setdefault("utils.snowflake_conn", _mock_conn)
sys.modules.setdefault("utils.snowflake_llm", MagicMock())
sys.modules.setdefault("utils.sanitize", MagicMock())

# Stub agent sub-modules (prevent crewai transitive imports)
for _mod in [
    "agents.ag1_detector", "agents.ag2_investigator",
    "agents.ag3_fix_advisor", "agents.ag5_validator", "agents.crew",
]:
    sys.modules.setdefault(_mod, MagicMock())

# Stub tool modules
for _mod in [
    "tools.composio_actions", "tools.demo_utils",
    "tools.query_snowflake", "tools.search_runbooks",
    "tools.find_similar_incidents",
]:
    sys.modules.setdefault(_mod, MagicMock())

from agents.manager import _safe_parse, _safe_float


class TestSafeParse:
    def test_parses_plain_json(self):
        raw = '{"severity": "P1", "blast_radius": ["svc-a"]}'
        result = _safe_parse(raw)
        assert result["severity"] == "P1"
        assert result["blast_radius"] == ["svc-a"]

    def test_strips_json_fences(self):
        raw = '```json\n{"verdict": "APPROVED"}\n```'
        result = _safe_parse(raw)
        assert result["verdict"] == "APPROVED"

    def test_strips_plain_fences(self):
        raw = '```\n{"confidence": 0.85}\n```'
        result = _safe_parse(raw)
        assert result["confidence"] == 0.85

    def test_extracts_json_from_surrounding_text(self):
        raw = 'Here is my analysis:\n{"root_cause": "memory leak", "confidence": 0.7}\nHope this helps.'
        result = _safe_parse(raw)
        assert result["root_cause"] == "memory leak"

    def test_empty_string_returns_error(self):
        result = _safe_parse("")
        assert "error" in result

    def test_none_returns_error(self):
        result = _safe_parse(None)
        assert "error" in result

    def test_unparseable_returns_error(self):
        result = _safe_parse("this is not json at all!!!")
        assert "error" in result

    def test_nested_json(self):
        raw = '{"fix_options": [{"rank": 1, "title": "Rollback", "risk_level": "LOW"}]}'
        result = _safe_parse(raw)
        assert len(result["fix_options"]) == 1
        assert result["fix_options"][0]["rank"] == 1

    def test_json_with_whitespace(self):
        raw = '  \n  {"severity": "P2"}  \n  '
        result = _safe_parse(raw)
        assert result["severity"] == "P2"

    def test_json_with_llm_preamble(self):
        raw = 'Based on my analysis, here is the output:\n```json\n{"verdict": "DEBATE", "confidence_adjustment": -0.15}\n```'
        result = _safe_parse(raw)
        assert result["verdict"] == "DEBATE"
        assert result["confidence_adjustment"] == -0.15


class TestSafeFloat:
    def test_int_input(self):
        assert _safe_float(1) == 1.0

    def test_float_input(self):
        assert _safe_float(0.75) == 0.75

    def test_string_float(self):
        assert _safe_float("0.85") == 0.85

    def test_string_int(self):
        assert _safe_float("1") == 1.0

    def test_string_with_whitespace(self):
        assert _safe_float("  0.5  ") == 0.5

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0
        assert _safe_float(None, 0.5) == 0.5

    def test_non_numeric_string_returns_default(self):
        assert _safe_float("not-a-number") == 0.0
        assert _safe_float("N/A", 0.3) == 0.3

    def test_empty_string_returns_default(self):
        assert _safe_float("") == 0.0

    def test_zero_is_valid(self):
        assert _safe_float(0) == 0.0
        assert _safe_float("0") == 0.0

    def test_large_value(self):
        assert _safe_float(999.999) == 999.999
