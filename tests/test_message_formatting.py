"""
Test 5 different incident scenarios for Slack + GitHub message formatting.
Validates: structured layout, no emojis in plain-text fallback, bold keywords,
file locations, evidence sources.

Run:  python -m pytest tests/test_message_formatting.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch Snowflake + Composio before importing composio_actions
_noop = MagicMock(return_value=None)
_empty_query = MagicMock(return_value=[])

with patch.dict(os.environ, {
    "COMPOSIO_API_KEY": "test-key",
    "GITHUB_REPO": "org/test-repo",
    "SLACK_CHANNEL": "test-channel",
}):
    with patch("utils.snowflake_conn.run_dml", _noop), \
         patch("utils.snowflake_conn.run_query", _empty_query):
        from tools.composio_actions import (
            post_slack_alert,
            create_github_issue,
            post_slack_alert_auto_resolved,
            post_slack_alert_escalation,
            post_slack_ci_confirmed,
            post_slack_ci_failure,
        )


def _extract_message(fn, *args, **kwargs):
    """
    Call the function with mocked Composio execution and return the Slack/GitHub payload dict.
    Handles both plain 'SENT' return (Slack/CI functions) and dict return (create_github_issue).
    """
    with patch("tools.composio_actions._already_sent", return_value=None), \
         patch("tools.composio_actions._record_action"), \
         patch("tools.composio_actions._execute_with_retry") as mock_exec, \
         patch("tools.composio_actions._update_status"):
        # Include 'data' so create_github_issue can parse issue_number and html_url
        mock_exec.return_value = {
            "successful": True,
            "data": {"number": 42, "html_url": "https://github.com/org/test-repo/issues/42"},
        }
        result = fn(*args, **kwargs)
        if isinstance(result, dict):
            assert result.get("status") == "SENT", f"Expected SENT status, got: {result}"
        else:
            assert result == "SENT", f"Expected SENT, got: {result}"
        payload = mock_exec.call_args[0][1]  # second positional arg to _execute_with_retry
        return payload


def _searchable(payload: dict) -> str:
    """
    Combine plain-text fallback + Block Kit JSON string for content searching.
    Block Kit Slack messages store rich content in 'blocks' (JSON string); the 'text'
    field is only a short plain-text fallback for notifications.
    """
    return payload.get("text", "") + " " + payload.get("blocks", "")


# Unicode emoji ranges to check for
EMOJI_RANGES = [
    (0x1F600, 0x1F64F),  # emoticons
    (0x1F300, 0x1F5FF),  # symbols & pictographs
    (0x1F680, 0x1F6FF),  # transport & map
    (0x1F900, 0x1F9FF),  # supplemental
    (0x2600, 0x26FF),    # misc symbols
    (0x2700, 0x27BF),    # dingbats
    (0xFE00, 0xFE0F),    # variation selectors
    (0x200D, 0x200D),    # ZWJ
]

def _has_emoji(text: str) -> list[str]:
    """Return list of emoji characters found."""
    found = []
    for ch in text:
        cp = ord(ch)
        for lo, hi in EMOJI_RANGES:
            if lo <= cp <= hi:
                found.append(f"U+{cp:04X} ({ch})")
                break
    return found


def _assert_no_emoji(text: str, context: str = ""):
    emojis = _has_emoji(text)
    assert not emojis, f"Found emojis in {context}: {emojis}"


def _assert_structured(text: str, required_fields: list[str], context: str = ""):
    for field in required_fields:
        assert field in text, f"Missing '{field}' in {context}:\n{text[:500]}"


class TestMessageFormatting(unittest.TestCase):
    """Test 5 real-world incident scenarios for message formatting quality."""

    # ── Scenario 1: API Latency Spike (Auto-Resolved) ────────────────────
    def test_scenario_1_api_latency_auto_resolved(self):
        """P2 latency spike on payment-service, auto-resolved with config rollback."""
        event_id = "evt-latency-001"
        service = "payment-service"
        severity = "P2"
        root_cause = "Connection pool exhaustion in payment-service caused by misconfigured max_connections=5 in database.yml. Under load, all connections were consumed, causing 30s+ query timeouts that cascaded to the API gateway."
        fix_options = [{
            "title": "Increase connection pool to max_connections=50",
            "risk_level": "LOW",
            "commands": ["sed -i 's/max_connections: 5/max_connections: 50/' config/database.yml", "kubectl rollout restart deployment/payment-service"],
            "file": "config/database.yml",
        }]
        evidence = ["snowflake_metrics", "connection_pool_logs", "api_gateway_traces"]
        blast = ["checkout-service", "order-service"]

        # Test Slack auto-resolved
        payload = _extract_message(
            post_slack_alert_auto_resolved,
            event_id, service, severity, root_cause,
            blast_radius=blast, fix_options=fix_options,
            confidence=0.92, mttr_seconds=47,
            evidence_sources=evidence, rule_applied="R1_HIGH_CONF_LOW_RISK",
        )
        # Block Kit: rich content is in 'blocks' JSON; 'text' is a plain-text fallback
        msg = _searchable(payload)
        _assert_no_emoji(payload["text"], "Scenario 1 Slack fallback")
        _assert_structured(msg, [
            "*Root Cause:*", "*Fix Applied:*", "*Commands Executed:*",
            "*Blast Radius:*", "*Evidence:*", "*Confidence:*", "*MTTR:*",
            "*Resolution Rule:*", "*Event ID:*", "config/database.yml",
        ], "Scenario 1 Slack")
        assert "R1_HIGH_CONF_LOW_RISK" in msg

        # Test GitHub issue
        payload_gh = _extract_message(
            create_github_issue,
            event_id, service, severity, root_cause,
            "[AUTO-RESOLVED] Increase connection pool",
            blast_radius=blast, fix_options=fix_options,
            evidence_sources=evidence, confidence=0.92,
            threshold_decision="AUTO_RESOLVE", rule_applied="R1_HIGH_CONF_LOW_RISK",
        )
        body = payload_gh["body"]
        _assert_no_emoji(body, "Scenario 1 GitHub")
        _assert_structured(body, [
            "## Incident Report", "### Summary", "### Root Cause Analysis",
            "### Recommended Fix", "### Resolution Checklist", "### Diagnostic Commands",
            "config/database.yml", "AUTO_RESOLVE", "payment-service",
        ], "Scenario 1 GitHub")
        # Verify table structure
        assert "| **Event ID**" in body
        assert "| **Confidence**" in body

    # ── Scenario 2: Memory Leak (Escalation — High Confidence) ───────────
    def test_scenario_2_memory_leak_escalation(self):
        """P1 memory leak in user-auth-service, escalated to human."""
        event_id = "evt-memleak-002"
        service = "user-auth-service"
        severity = "P1"
        root_cause = "Unbounded session cache in AuthSessionManager.java growing at 2MB/min. GC unable to reclaim due to strong references in ConcurrentHashMap. OOM kill triggered at 4GB heap limit after ~33 minutes of operation."
        fix_options = [
            {
                "title": "Add TTL-based eviction to session cache",
                "risk_level": "MEDIUM",
                "commands": ["git apply patches/session-cache-ttl.patch"],
                "file": "src/main/java/auth/AuthSessionManager.java",
            },
            {
                "title": "Emergency: restart pods with increased memory limit",
                "risk_level": "LOW",
                "commands": ["kubectl set resources deployment/user-auth-service --limits=memory=8Gi"],
                "file": "k8s/deployment.yaml",
            },
        ]
        evidence = ["heap_dump_analysis", "gc_logs", "kubernetes_events", "prometheus_metrics"]
        blast = ["api-gateway", "session-store", "billing-service"]

        payload = _extract_message(
            post_slack_alert_escalation,
            event_id, service, severity, root_cause,
            blast_radius=blast, fix_options=fix_options,
            urgency="HIGH_CONFIDENCE", incident_type="PERFORMANCE",
            confidence=0.78, evidence_sources=evidence,
            rule_applied="R3_HIGH_RISK_ESCALATE",
        )
        # Block Kit: rich content lives in 'blocks' JSON
        msg = _searchable(payload)
        _assert_no_emoji(payload["text"], "Scenario 2 Slack fallback")
        _assert_structured(msg, [
            "HIGH CONFIDENCE",           # urgency band in Block Kit header
            "*Service:*", "*Incident Type:*",
            "*Root Cause:*", "*Blast Radius:*", "*Confidence:*", "*Evidence:*",
            "*Fix Option 1:*", "*Fix Option 2:*", "*Resolution Rule:*",
        ], "Scenario 2 Slack")
        assert "PERFORMANCE" in msg
        assert "awaiting human approval" in msg

    # ── Scenario 3: Security Vulnerability (Escalation — Immediate) ──────
    def test_scenario_3_security_vulnerability_immediate(self):
        """P1 SQL injection in search-service, immediate escalation."""
        event_id = "evt-sqli-003"
        service = "search-service"
        severity = "P1"
        root_cause = "Unsanitized user input in SearchController.handleQuery() passed directly to raw SQL query via string concatenation. Exploitable via crafted search_term parameter: GET /api/search?q=' OR 1=1 --. Affects all endpoints using SearchDAO.rawQuery()."
        fix_options = [{
            "title": "Replace raw SQL with parameterized queries in SearchDAO",
            "risk_level": "MEDIUM",
            "commands": ["git apply patches/parameterize-search-dao.patch", "mvn test -pl search-service"],
            "file": "src/main/java/search/SearchDAO.java",
        }]
        evidence = ["waf_logs", "sql_error_logs", "request_traces", "vulnerability_scan"]
        blast = ["database-primary", "user-data-service"]

        payload = _extract_message(
            post_slack_alert_escalation,
            event_id, service, severity, root_cause,
            blast_radius=blast, fix_options=fix_options,
            urgency="IMMEDIATE", incident_type="SECURITY",
            confidence=0.95, evidence_sources=evidence,
            rule_applied="R5_SECURITY_ESCALATE",
        )
        msg = _searchable(payload)
        _assert_no_emoji(payload["text"], "Scenario 3 Slack fallback")
        _assert_structured(msg, [
            "SECURITY INCIDENT", "Human Review Required",  # Block Kit header text
            "*Service:*", "*Incident Type:*", "SECURITY",
            "*Root Cause:*", "SearchDAO", "SearchController",
            "*Fix Option 1:*",
            "NO AUTO-ACTIONS TAKEN",
            "evt-sqli-003",
        ], "Scenario 3 Slack")

        # GitHub issue for security incident
        payload_gh = _extract_message(
            create_github_issue,
            event_id, service, severity, root_cause,
            "Replace raw SQL with parameterized queries",
            blast_radius=blast, fix_options=fix_options,
            evidence_sources=evidence, confidence=0.95,
            threshold_decision="HUMAN_ESCALATION", rule_applied="R5_SECURITY_ESCALATE",
        )
        body = payload_gh["body"]
        _assert_no_emoji(body, "Scenario 3 GitHub")
        assert "HUMAN_ESCALATION" in body
        assert "SearchDAO.java" in body  # present in fix_options table via 'file' field
        assert "### Diagnostic Commands" in body

    # ── Scenario 4: Deployment Failure (Low Confidence) ──────────────────
    def test_scenario_4_deployment_failure_low_confidence(self):
        """P3 flaky deployment on notification-service, low confidence."""
        event_id = "evt-deploy-004"
        service = "notification-service"
        severity = "P3"
        root_cause = "Intermittent ImagePullBackOff on notification-service pods. Docker registry returned HTTP 429 (rate limited) for image pull attempts. Possibly transient infrastructure issue or registry credential expiry."
        fix_options = [{
            "title": "Retry deployment with exponential backoff",
            "risk_level": "LOW",
            "commands": ["kubectl rollout restart deployment/notification-service"],
            "file": "k8s/notification-service/deployment.yaml",
        }]
        evidence = ["kubernetes_events", "pod_logs"]
        blast = []

        payload = _extract_message(
            post_slack_alert_escalation,
            event_id, service, severity, root_cause,
            blast_radius=blast, fix_options=fix_options,
            urgency="LOW_CONFIDENCE", incident_type="INFRASTRUCTURE",
            confidence=0.35, evidence_sources=evidence,
            rule_applied="R4_LOW_CONF_ESCALATE",
        )
        msg = _searchable(payload)
        _assert_no_emoji(payload["text"], "Scenario 4 Slack fallback")
        _assert_structured(msg, [
            "LOW CONFIDENCE",            # Block Kit header band
            "*Service:*", "notification-service",
            "*Root Cause:*", "ImagePullBackOff",
            "immediate human investigation required",
            "evt-deploy-004",
        ], "Scenario 4 Slack")

    # ── Scenario 5: CI Pipeline Failure + Recovery ───────────────────────
    def test_scenario_5_ci_failure_and_recovery(self):
        """CI failure on data-pipeline-service, then CI pass after fix."""
        event_id = "evt-ci-005"
        service = "data-pipeline-service"

        # Part A: CI failure alert (uses plain text format, not Block Kit)
        payload_fail = _extract_message(
            post_slack_ci_failure,
            event_id, service,
            workflow="build-and-test",
            branch="fix/etl-timeout",
            sha="a1b2c3d",
            conclusion="failure",
            url="https://github.com/org/repo/actions/runs/12345",
        )
        msg_fail = payload_fail["text"]
        _assert_no_emoji(msg_fail, "Scenario 5 CI Fail Slack")
        _assert_structured(msg_fail, [
            "*[CI FAIL] Pipeline Failure",
            "*Workflow:*", "build-and-test",
            "*Conclusion:*", "FAILURE",
            "*Branch:*", "fix/etl-timeout",
            "*Commit:*", "a1b2c3d",
            "autonomous agents triggered",
            "evt-ci-005",
        ], "Scenario 5 CI Fail Slack")

        # Part B: CI confirmed (fix verified, plain text format)
        payload_pass = _extract_message(
            post_slack_ci_confirmed,
            event_id, service,
            workflow="build-and-test",
            branch="fix/etl-timeout",
            sha="d4e5f6g",
            url="https://github.com/org/repo/actions/runs/12346",
        )
        msg_pass = payload_pass["text"]
        _assert_no_emoji(msg_pass, "Scenario 5 CI Pass Slack")
        _assert_structured(msg_pass, [
            "*[CI PASS] Fix Verified",
            "*Workflow:*", "build-and-test",
            "*Branch:*", "fix/etl-timeout",
            "*Commit:*", "d4e5f6g",
            "All checks passed",
            "evt-ci-005",
        ], "Scenario 5 CI Pass Slack")

    # ── Cross-cutting: GitHub issue has table + checklist + commands ──────
    def test_github_issue_has_complete_structure(self):
        """Verify GitHub issue contains all required sections."""
        payload = _extract_message(
            create_github_issue,
            "evt-struct-check", "test-service", "P2",
            "Test root cause for structure validation",
            "Apply hotfix patch",
            blast_radius=["svc-a", "svc-b"],
            fix_options=[{
                "title": "Hotfix patch",
                "risk_level": "LOW",
                "commands": ["git apply fix.patch"],
                "file": "src/main/App.java",
            }],
            evidence_sources=["metrics", "traces", "logs"],
            confidence=0.85,
            threshold_decision="AUTO_RESOLVE",
            rule_applied="R1_HIGH_CONF_LOW_RISK",
        )
        body = payload["body"]
        title = payload["title"]

        # Title format
        assert title.startswith("[P2]")
        assert "test-service" in title

        # All required sections
        sections = [
            "## Incident Report",
            "### Summary",
            "### Root Cause Analysis",
            "### Recommended Fix",
            "### Resolution Checklist",
            "### Diagnostic Commands",
        ]
        for s in sections:
            assert s in body, f"Missing section: {s}"

        # Summary table fields
        table_fields = ["Event ID", "Service", "Severity", "Confidence", "Decision", "Rule", "Blast Radius", "Evidence"]
        for f in table_fields:
            assert f"**{f}**" in body, f"Missing table field: {f}"

        # Fix options table
        assert "| # | Fix | Risk | Commands | File / Location |" in body
        assert "App.java" in body

        # Checklist items
        checklist_items = [
            "Root cause confirmed", "Fix verified in staging",
            "Fix deployed to production", "Service health metrics",
            "Blast radius services", "Post-mortem document", "Runbook updated",
        ]
        for item in checklist_items:
            assert item in body, f"Missing checklist item: {item}"

        # Diagnostic commands
        assert "curl -s http://test-service:8080/health" in body
        assert "kubectl logs -l app=test-service" in body
        assert "snowsql" in body

        _assert_no_emoji(body, "Structure check GitHub")
        _assert_no_emoji(title, "Structure check GitHub title")


if __name__ == "__main__":
    unittest.main()
