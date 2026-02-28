"""
Unit tests for the Autonomous Resolution Threshold Engine.

All 7 rules are tested with no external dependencies (no Snowflake, no Composio).
fix_proven_override is used in event details to bypass the DB lookup.
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

from agents.manager import _evaluate_threshold, _safe_parse, _safe_float, ANOMALY_TO_INCIDENT_TYPE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_event(anomaly_type="db_pool_exhaustion", service="payment-service", **detail_overrides):
    details = {"fix_proven_override": False, **detail_overrides}
    return {"event_id": "test-001", "service": service,
            "anomaly_type": anomaly_type, "severity": "P2", "details": details}


def _make_detection(blast_radius=None):
    return {"severity": "P2", "blast_radius": blast_radius or [], "classification": "test"}


def _make_investigation(confidence=0.85, action="rollback"):
    return {"root_cause": "deploy regression", "confidence": confidence,
            "evidence_sources": ["runbook", "metrics"], "recommended_action": action}


def _make_fix_options(risk="MEDIUM"):
    return [{"rank": 1, "title": "Rollback", "commands": ["kubectl rollout undo"],
             "estimated_time": "5m", "risk_level": risk, "rollback": "re-deploy"}]


# ---------------------------------------------------------------------------
# RULE 1 — Security / Data Integrity always escalates
# ---------------------------------------------------------------------------

class TestRule1:
    def test_security_incident_always_escalates(self):
        event = _make_event("credential_stuffing")
        result = _evaluate_threshold(event, _make_detection(), _make_investigation(0.99),
                                     _make_fix_options("LOW"), approved=True)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_1"
        assert result["urgency"] == "IMMEDIATE"

    def test_data_integrity_always_escalates(self):
        event = _make_event("data_corruption")
        result = _evaluate_threshold(event, _make_detection(), _make_investigation(0.99),
                                     _make_fix_options("LOW"), approved=True)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_1"

    def test_auth_breach_escalates(self):
        event = _make_event("auth_breach")
        result = _evaluate_threshold(event, _make_detection(), _make_investigation(0.99),
                                     _make_fix_options("LOW"), approved=True)
        assert result["rule_applied"] == "RULE_1"

    def test_performance_incident_passes_rule1(self):
        event = _make_event("db_pool_exhaustion")
        result = _evaluate_threshold(event, _make_detection(), _make_investigation(0.5),
                                     _make_fix_options(), approved=False)
        assert result["rule_applied"] != "RULE_1"


# ---------------------------------------------------------------------------
# RULE 2 — Validator did not approve
# ---------------------------------------------------------------------------

class TestRule2:
    def test_unapproved_escalates(self):
        event = _make_event("latency_regression")
        result = _evaluate_threshold(event, _make_detection(), _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=False)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_2"
        assert result["urgency"] == "HIGH"

    def test_approved_passes_rule2(self):
        event = _make_event("latency_regression")
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=True)
        assert result["rule_applied"] != "RULE_2"


# ---------------------------------------------------------------------------
# RULE 3 — Blast radius > 2
# ---------------------------------------------------------------------------

class TestRule3:
    def test_wide_blast_radius_escalates(self):
        event = _make_event()
        detection = _make_detection(["svc-a", "svc-b", "svc-c"])
        result = _evaluate_threshold(event, detection, _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=True)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_3"

    def test_exactly_2_services_passes_rule3(self):
        event = _make_event()
        detection = _make_detection(["svc-a", "svc-b"])
        result = _evaluate_threshold(event, detection, _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=True)
        assert result["rule_applied"] != "RULE_3"

    def test_blast_radius_override_in_details(self):
        event = _make_event(blast_radius_override=5)
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=True)
        assert result["rule_applied"] == "RULE_3"
        assert result["blast_radius_count"] == 5


# ---------------------------------------------------------------------------
# RULE 4 — AUTO_RESOLVE (requires env vars)
# ---------------------------------------------------------------------------

class TestRule4:
    def test_auto_resolve_all_conditions_met(self):
        event = _make_event(fix_proven_override=True)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        os.environ["AUTO_FIX_CONFIDENCE_THRESHOLD"] = "0.90"
        os.environ.pop("AUTO_FIX_WHITELIST", None)
        try:
            result = _evaluate_threshold(event, _make_detection([]),
                                         _make_investigation(0.95),
                                         _make_fix_options("LOW"), approved=True)
            assert result["decision"] == "AUTO_RESOLVE"
            assert result["rule_applied"] == "RULE_4"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)

    def test_no_auto_resolve_when_disabled(self):
        event = _make_event(fix_proven_override=True)
        os.environ.pop("AUTO_FIX_ENABLED", None)
        result = _evaluate_threshold(event, _make_detection([]),
                                     _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=True)
        assert result["decision"] != "AUTO_RESOLVE"

    def test_no_auto_resolve_when_risk_not_low(self):
        event = _make_event(fix_proven_override=True)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        try:
            result = _evaluate_threshold(event, _make_detection([]),
                                         _make_investigation(0.95),
                                         _make_fix_options("HIGH"), approved=True)
            assert result["decision"] != "AUTO_RESOLVE"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)

    def test_no_auto_resolve_when_confidence_too_low(self):
        event = _make_event(fix_proven_override=True)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        os.environ["AUTO_FIX_CONFIDENCE_THRESHOLD"] = "0.90"
        try:
            result = _evaluate_threshold(event, _make_detection([]),
                                         _make_investigation(0.80),
                                         _make_fix_options("LOW"), approved=True)
            assert result["decision"] != "AUTO_RESOLVE"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)

    def test_no_auto_resolve_when_fix_not_proven(self):
        event = _make_event(fix_proven_override=False)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        try:
            result = _evaluate_threshold(event, _make_detection([]),
                                         _make_investigation(0.95),
                                         _make_fix_options("LOW"), approved=True)
            assert result["decision"] != "AUTO_RESOLVE"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)

    def test_whitelist_blocks_non_whitelisted_service(self):
        event = _make_event(service="payment-service", fix_proven_override=True)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        os.environ["AUTO_FIX_WHITELIST"] = "order-service,notification-service"
        try:
            result = _evaluate_threshold(event, _make_detection([]),
                                         _make_investigation(0.95),
                                         _make_fix_options("LOW"), approved=True)
            assert result["decision"] != "AUTO_RESOLVE"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)
            os.environ.pop("AUTO_FIX_WHITELIST", None)

    def test_whitelist_allows_whitelisted_service(self):
        event = _make_event(service="payment-service", fix_proven_override=True)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        os.environ["AUTO_FIX_WHITELIST"] = "payment-service,order-service"
        os.environ["AUTO_FIX_CONFIDENCE_THRESHOLD"] = "0.90"
        try:
            result = _evaluate_threshold(event, _make_detection([]),
                                         _make_investigation(0.95),
                                         _make_fix_options("LOW"), approved=True)
            assert result["decision"] == "AUTO_RESOLVE"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)
            os.environ.pop("AUTO_FIX_WHITELIST", None)


# ---------------------------------------------------------------------------
# RULE 5 / 6 / 7 — Confidence bands
# ---------------------------------------------------------------------------

class TestConfidenceBands:
    def test_high_confidence_rule5(self):
        event = _make_event()
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.80),
                                     _make_fix_options(), approved=True)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_5"
        assert result["urgency"] == "HIGH_CONFIDENCE"

    def test_medium_confidence_rule6(self):
        event = _make_event()
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.60),
                                     _make_fix_options(), approved=True)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_6"
        assert result["urgency"] == "MEDIUM_CONFIDENCE"

    def test_low_confidence_rule7(self):
        event = _make_event()
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.30),
                                     _make_fix_options(), approved=True)
        assert result["decision"] == "HUMAN_ESCALATION"
        assert result["rule_applied"] == "RULE_7"
        assert result["urgency"] == "LOW_CONFIDENCE"

    def test_confidence_boundary_75_is_rule5(self):
        event = _make_event()
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.75),
                                     _make_fix_options(), approved=True)
        assert result["rule_applied"] == "RULE_5"

    def test_confidence_boundary_50_is_rule6(self):
        event = _make_event()
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.50),
                                     _make_fix_options(), approved=True)
        assert result["rule_applied"] == "RULE_6"

    def test_confidence_just_below_50_is_rule7(self):
        event = _make_event()
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.49),
                                     _make_fix_options(), approved=True)
        assert result["rule_applied"] == "RULE_7"


# ---------------------------------------------------------------------------
# Demo overrides
# ---------------------------------------------------------------------------

class TestDemoOverrides:
    def test_confidence_override_in_details(self):
        event = _make_event(confidence_override=0.30)
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.95),
                                     _make_fix_options(), approved=True)
        assert result["confidence"] == 0.30
        assert result["rule_applied"] == "RULE_7"

    def test_approved_override_false_triggers_rule2(self):
        event = _make_event(approved_override=False)
        result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.95),
                                     _make_fix_options("LOW"), approved=True)
        assert result["rule_applied"] == "RULE_2"

    def test_risk_level_override(self):
        event = _make_event(risk_level_override="LOW", fix_proven_override=True)
        os.environ["AUTO_FIX_ENABLED"] = "true"
        os.environ["AUTO_FIX_CONFIDENCE_THRESHOLD"] = "0.90"
        try:
            result = _evaluate_threshold(event, _make_detection([]), _make_investigation(0.95),
                                         _make_fix_options("HIGH"), approved=True)
            assert result["risk_level"] == "LOW"
            assert result["decision"] == "AUTO_RESOLVE"
        finally:
            os.environ.pop("AUTO_FIX_ENABLED", None)


# ---------------------------------------------------------------------------
# Anomaly type mapping
# ---------------------------------------------------------------------------

class TestAnomalyTypeMapping:
    def test_known_security_types(self):
        for t in ("credential_stuffing", "auth_breach", "unauthorized_access"):
            assert ANOMALY_TO_INCIDENT_TYPE[t] == "SECURITY"

    def test_known_data_integrity_types(self):
        for t in ("data_corruption", "silent_data_corruption", "data_integrity_violation"):
            assert ANOMALY_TO_INCIDENT_TYPE[t] == "DATA_INTEGRITY"

    def test_ci_failure_types_are_performance(self):
        for t in ("ci_failure", "test_failure", "build_failure"):
            assert ANOMALY_TO_INCIDENT_TYPE[t] == "PERFORMANCE"

    def test_performance_types(self):
        for t in ("db_pool_exhaustion", "latency_regression", "error_rate_spike"):
            assert ANOMALY_TO_INCIDENT_TYPE[t] == "PERFORMANCE"
