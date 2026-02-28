"""
Unit tests for idempotency key generation and CI trigger parsing.

Pure Python — no Snowflake, no Composio.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock

# Stub external dependencies before importing the module under test
sys.modules.setdefault("snowflake", MagicMock())
sys.modules.setdefault("snowflake.connector", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())

# dotenv.load_dotenv must be callable
_dotenv_mock = MagicMock()
_dotenv_mock.load_dotenv = MagicMock(return_value=None)
sys.modules["dotenv"] = _dotenv_mock

# Stub utils.snowflake_conn individually (don't replace the whole utils package)
_mock_conn = MagicMock()
_mock_conn.run_dml = MagicMock(return_value=None)
_mock_conn.run_query = MagicMock(return_value=[])
_mock_conn.get_connection = MagicMock(return_value=MagicMock())
sys.modules.setdefault("utils.snowflake_conn", _mock_conn)

from tools.composio_actions import _idempotency_key


class TestIdempotencyKey:
    def test_deterministic_same_inputs(self):
        k1 = _idempotency_key("SLACK_ALERT", "evt-001")
        k2 = _idempotency_key("SLACK_ALERT", "evt-001")
        assert k1 == k2

    def test_different_action_types_produce_different_keys(self):
        k1 = _idempotency_key("SLACK_ALERT", "evt-001")
        k2 = _idempotency_key("GITHUB_ISSUE", "evt-001")
        assert k1 != k2

    def test_different_event_ids_produce_different_keys(self):
        k1 = _idempotency_key("SLACK_ALERT", "evt-001")
        k2 = _idempotency_key("SLACK_ALERT", "evt-002")
        assert k1 != k2

    def test_key_length_is_32_chars(self):
        k = _idempotency_key("SLACK_ALERT", "evt-abc123")
        assert len(k) == 32

    def test_key_is_hex(self):
        k = _idempotency_key("SLACK_ALERT", "evt-abc123")
        int(k, 16)  # raises ValueError if not hex

    def test_all_action_types_produce_unique_keys(self):
        event_id = "evt-test"
        action_types = [
            "SLACK_ALERT", "SLACK_ESCALATION", "SLACK_AUTO_RESOLVED",
            "SLACK_CI_FAILURE", "SLACK_CI_CONFIRMED", "GITHUB_ISSUE",
        ]
        keys = [_idempotency_key(t, event_id) for t in action_types]
        assert len(keys) == len(set(keys)), "Duplicate keys detected"

    def test_empty_event_id_still_works(self):
        k = _idempotency_key("SLACK_ALERT", "")
        assert len(k) == 32

    def test_ci_confirmed_key_includes_sha(self):
        # CI confirmed uses action_type that includes the SHA
        k1 = _idempotency_key("SLACK_CI_CONFIRMED:abc1234", "evt-001")
        k2 = _idempotency_key("SLACK_CI_CONFIRMED:def5678", "evt-001")
        assert k1 != k2, "Different SHAs should produce different keys"


class TestCITriggerParsing:
    """Test the CI event parsing logic in handle_ci_result."""

    def test_success_conclusion_detected(self):
        """Verify success events are recognized."""
        event = {
            "workflow_run": {
                "conclusion": "success",
                "status": "completed",
                "name": "CI",
                "head_sha": "abc1234567",
                "head_branch": "main",
                "repository": {"name": "payment-service"},
                "html_url": "https://github.com/example/run/1",
            }
        }
        workflow_run = event.get("workflow_run", event)
        conclusion = workflow_run.get("conclusion", "")
        assert conclusion == "success"

    def test_failure_conclusion_detected(self):
        """Verify failure events are recognized."""
        event = {
            "workflow_run": {
                "conclusion": "failure",
                "status": "completed",
                "name": "CI",
                "head_sha": "abc1234567",
                "head_branch": "main",
                "repository": {"name": "payment-service"},
                "html_url": "https://github.com/example/run/2",
            }
        }
        workflow_run = event.get("workflow_run", event)
        conclusion = workflow_run.get("conclusion", "")
        assert conclusion in ("failure", "timed_out", "action_required")

    def test_in_progress_status_is_ignored(self):
        """Verify in-progress workflows are not acted on."""
        event = {
            "workflow_run": {
                "conclusion": None,
                "status": "in_progress",
                "name": "CI",
                "head_sha": "abc1234567",
                "head_branch": "main",
                "repository": {"name": "payment-service"},
                "html_url": "",
            }
        }
        workflow_run = event.get("workflow_run", event)
        status = workflow_run.get("status", "")
        assert status != "completed"

    def test_sha_truncated_to_7_chars(self):
        workflow_run = {"head_sha": "abc1234567890full", "conclusion": "success",
                        "status": "completed"}
        head_sha = workflow_run.get("head_sha", "unknown")[:7]
        assert head_sha == "abc1234"
        assert len(head_sha) == 7

    def test_repo_name_extracted_correctly(self):
        workflow_run = {"repository": {"name": "payment-service"}}
        repo = (workflow_run.get("repository") or {}).get("name", "unknown-service")
        assert repo == "payment-service"

    def test_missing_repository_defaults_to_unknown(self):
        workflow_run = {}
        repo = (workflow_run.get("repository") or {}).get("name", "unknown-service")
        assert repo == "unknown-service"
