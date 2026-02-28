"""
IncidentDNA — Agent Manager
Orchestrates Ag1 → Ag2 → Ag5 (debate loop) → Threshold Engine → Actions → DNA storage.

Entry point: run_incident_crew(event: dict) -> dict
Called directly by ingestion/trigger_listener.py (no HTTP bridge).
"""

import json
import os
import re
from datetime import datetime, timezone
from agents.ag1_detector import make_detector, detector_task
from agents.ag2_investigator import make_investigator, investigator_task
from agents.ag3_fix_advisor import make_fix_advisor, fix_advisor_task
from agents.ag5_validator import make_validator, validator_task
from agents.crew import make_crew
from tools.composio_actions import (
    post_slack_alert, create_github_issue,
    post_slack_alert_auto_resolved, post_slack_alert_escalation,
)
from utils.snowflake_conn import run_dml, run_query
from tools.demo_utils import simulate_fix_execution, inject_recovery_metrics

MAX_DEBATE_ROUNDS = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_parse(raw: str) -> dict:
    """
    Parse LLM output to dict. Handles:
      - Pure JSON strings
      - JSON wrapped in ```json ... ``` fences
      - JSON embedded in a longer response (extracts first {...} block)
    """
    if not raw:
        return {"error": "empty_response"}

    # Strip markdown fences
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.MULTILINE).strip()
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Extract first JSON object using non-greedy match with balanced braces
    # Find the first { and then find its matching }
    start = cleaned.find('{')
    if start != -1:
        depth = 0
        for i, char in enumerate(cleaned[start:], start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start:i+1])
                    except json.JSONDecodeError:
                        break

    return {"error": "parse_failed", "raw": raw[:500]}


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, handling string numbers from LLM."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return default
    return default


def _log_decision(
    event_id: str,
    agent_name: str,
    input_data: dict,
    output_data: dict,
    reasoning: str,
    confidence: float,
) -> None:
    """Write an agent decision step to AI.DECISIONS (read by P3 dashboard)."""
    try:
        run_dml(
            """INSERT INTO AI.DECISIONS
                   (event_id, agent_name, output, reasoning, confidence)
               SELECT %s, %s, PARSE_JSON(%s), %s, %s""",
            (
                event_id,
                agent_name,
                json.dumps(output_data),
                reasoning[:4000],  # truncate very long reasoning
                round(float(confidence), 4),
            ),
        )
    except Exception as e:
        print(f"[MANAGER] Warning: failed to log decision for {agent_name}: {e}")


def _defaults(detection: dict, event: dict) -> dict:
    """Fill in safe defaults if LLM output is missing fields."""
    return {
        "severity":       detection.get("severity", event.get("severity", "P3")),
        "blast_radius":   detection.get("blast_radius", []),
        "classification": detection.get("classification", event.get("anomaly_type", "unknown")),
    }


# ---------------------------------------------------------------------------
# Autonomous Resolution Threshold Engine
# ---------------------------------------------------------------------------

ANOMALY_TO_INCIDENT_TYPE = {
    "db_pool_exhaustion":       "PERFORMANCE",
    "latency_regression":       "PERFORMANCE",
    "post_deploy_error_rate":   "PERFORMANCE",
    "error_rate_spike":         "PERFORMANCE",
    "latency_p99_spike":        "PERFORMANCE",
    "cpu_pct_spike":            "PERFORMANCE",
    "memory_leak":              "PERFORMANCE",
    "data_corruption":          "DATA_INTEGRITY",
    "silent_data_corruption":   "DATA_INTEGRITY",
    "data_integrity_violation": "DATA_INTEGRITY",
    "credential_stuffing":      "SECURITY",
    "auth_breach":              "SECURITY",
    "unauthorized_access":      "SECURITY",
    "cascading_failure":        "AVAILABILITY",
    "service_down":             "AVAILABILITY",
    "gradual_degradation":      "TREND",
    "slow_burn":                "TREND",
    # CI/CD feedback loop
    "ci_failure":               "PERFORMANCE",
    "test_failure":             "PERFORMANCE",
    "build_failure":            "PERFORMANCE",
}


def _check_fix_proven(service: str, root_cause: str) -> bool:
    """Check AI.INCIDENT_HISTORY for a past successful fix matching this service+root_cause."""
    try:
        # Extract first few significant words for LIKE match
        words = [w for w in root_cause.lower().split() if len(w) > 3][:3]
        if not words:
            return False
        like_pattern = "%" + "%".join(words) + "%"
        rows = run_query(
            """SELECT COUNT(*) AS match_count
               FROM AI.INCIDENT_HISTORY
               WHERE service_name = %s
                 AND LOWER(root_cause) LIKE %s
                 AND confidence >= 0.75""",
            (service, like_pattern),
        )
        return rows[0]["MATCH_COUNT"] > 0 if rows else False
    except Exception as e:
        print(f"[THRESHOLD] fix_proven check failed (defaulting to False): {e}")
        return False


def _evaluate_threshold(
    event: dict,
    detection: dict,
    investigation: dict,
    fix_options: list[dict],
    approved: bool,
) -> dict:
    """
    Autonomous Resolution Threshold Engine.
    Evaluates rules in order (first match wins) to decide AUTO_RESOLVE vs HUMAN_ESCALATION.
    """
    # --- Determine incident_type ---
    incident_type = event.get("incident_type") or ANOMALY_TO_INCIDENT_TYPE.get(
        event.get("anomaly_type", ""), "PERFORMANCE"
    )

    # --- Extract demo overrides (only used by run_demo.py for deterministic results) ---
    details = event.get("details", {}) if isinstance(event.get("details"), dict) else {}

    # --- Determine confidence (with optional override for demos) ---
    confidence = _safe_float(investigation.get("confidence", 0), 0.0)
    if details.get("confidence_override") is not None:
        confidence = _safe_float(details["confidence_override"], confidence)

    # --- Determine risk_level (with optional override) ---
    risk_level = "MEDIUM"
    if details.get("risk_level_override") is not None:
        risk_level = str(details["risk_level_override"]).upper()
    elif fix_options:
        risk_level = str(fix_options[0].get("risk_level", "MEDIUM")).upper()

    # --- Determine blast_radius_count (with fallback + override) ---
    blast_radius = detection.get("blast_radius", [])
    if not blast_radius:
        blast_radius = details.get("affected_services", [])
    blast_radius_count = len(blast_radius) if isinstance(blast_radius, list) else 0
    if details.get("blast_radius_override") is not None:
        blast_radius_count = int(details["blast_radius_override"])

    # --- Determine fix_proven (with optional override) ---
    if details.get("fix_proven_override") is not None:
        fix_proven = bool(details["fix_proven_override"])
    else:
        fix_proven = _check_fix_proven(event["service"], investigation.get("root_cause", ""))

    # --- Override approved status for demo determinism ---
    if details.get("approved_override") is not None:
        approved = bool(details["approved_override"])

    # --- Apply rules (first match wins) ---

    def _decision(decision, rule, urgency, reason):
        return {
            "decision": decision,
            "rule_applied": rule,
            "urgency": urgency,
            "rule_description": reason,
            "incident_type": incident_type,
            "confidence": round(confidence, 4),
            "fix_proven": fix_proven,
            "risk_level": risk_level,
            "blast_radius_count": blast_radius_count,
        }

    # RULE 1: Hard block on SECURITY or DATA_INTEGRITY
    if incident_type in ("SECURITY", "DATA_INTEGRITY"):
        return _decision(
            "HUMAN_ESCALATION", "RULE_1", "IMMEDIATE",
            f"Hard block: {incident_type} incidents always require human review",
        )

    # RULE 2: Hard block if validator did NOT approve
    if not approved:
        return _decision(
            "HUMAN_ESCALATION", "RULE_2", "HIGH",
            "Validator did not approve the investigation",
        )

    # RULE 3: Hard block if blast_radius > 2 services
    if blast_radius_count > 2:
        return _decision(
            "HUMAN_ESCALATION", "RULE_3", "HIGH",
            f"Blast radius too wide: {blast_radius_count} services affected (limit: 2)",
        )

    # RULE 4: Auto-resolve if confidence >= threshold AND risk LOW AND fix_proven
    #         Also requires AUTO_FIX_ENABLED=true and service in AUTO_FIX_WHITELIST
    auto_fix_enabled = os.getenv("AUTO_FIX_ENABLED", "false").lower() == "true"
    conf_threshold = float(os.getenv("AUTO_FIX_CONFIDENCE_THRESHOLD", "0.90"))
    whitelist_raw = os.getenv("AUTO_FIX_WHITELIST", "")
    whitelist = [s.strip() for s in whitelist_raw.split(",") if s.strip()]
    service_name = event.get("service", "")

    if (
        auto_fix_enabled
        and confidence >= conf_threshold
        and risk_level == "LOW"
        and fix_proven
        and (not whitelist or service_name in whitelist)
    ):
        return _decision(
            "AUTO_RESOLVE", "RULE_4", None,
            f"Confidence {confidence:.0%} >= {conf_threshold:.0%}, risk LOW, fix proven, service whitelisted -> auto-resolve",
        )

    # RULE 5: High confidence escalation
    if confidence >= 0.75:
        return _decision(
            "HUMAN_ESCALATION", "RULE_5", "HIGH_CONFIDENCE",
            f"Confidence {confidence:.0%} meets high band but not all auto-resolve conditions met",
        )

    # RULE 6: Medium confidence escalation
    if confidence >= 0.50:
        return _decision(
            "HUMAN_ESCALATION", "RULE_6", "MEDIUM_CONFIDENCE",
            f"Confidence {confidence:.0%} in medium band — multiple hypotheses possible",
        )

    # RULE 7: Low confidence (default)
    return _decision(
        "HUMAN_ESCALATION", "RULE_7", "LOW_CONFIDENCE",
        f"Low confidence {confidence:.0%} — immediate human investigation required",
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_incident_crew(event: dict) -> dict:
    """
    Full incident pipeline. Called by ingestion/trigger_listener.py.

    Args:
        event: {
            "event_id":    str,   # unique ID (e.g. "evt-abc123")
            "service":     str,   # e.g. "payment-service"
            "anomaly_type": str,  # e.g. "db_pool_exhaustion"
            "severity":    str,   # initial signal: "P1"|"P2"|"P3"
            "details":     dict,  # optional extra context
        }

    Returns:
        Result dict with all pipeline outputs.
    """
    print(f"\n{'='*60}")
    print(f"[MANAGER] Pipeline started — event_id={event['event_id']}")
    print(f"[MANAGER] Service={event['service']}  Anomaly={event['anomaly_type']}")
    print(f"{'='*60}\n")

    # Track MTTR phase timestamps
    ts_detected = datetime.now(timezone.utc)

    # ── CI Failure: send immediate Slack alert before agents run (agents take ~90s) ──
    details = event.get("details", {}) if isinstance(event.get("details"), dict) else {}
    if event.get("anomaly_type") in ("ci_failure", "test_failure", "build_failure"):
        try:
            from tools.composio_actions import post_slack_ci_failure
            post_slack_ci_failure(
                event_id   = event["event_id"],
                service    = event["service"],
                workflow   = details.get("workflow", "CI"),
                branch     = details.get("branch", "main"),
                sha        = details.get("commit_sha", "unknown"),
                conclusion = details.get("conclusion", "failure"),
                url        = details.get("run_url", ""),
            )
            print(f"[MANAGER] Immediate CI failure alert sent to Slack")
        except Exception as e:
            print(f"[MANAGER] Immediate CI alert failed (non-fatal): {e}")

    # ── Phase 1: Detect ──────────────────────────────────────────────────────
    print("[MANAGER] Phase 1: Detection")
    ag1 = make_detector()
    t1  = detector_task(ag1, event)
    detection_raw = make_crew([ag1], [t1]).kickoff().raw
    detection     = _safe_parse(detection_raw)
    detection     = {**_defaults(detection, event), **detection}

    _log_decision(
        event_id   = event["event_id"],
        agent_name = "ag1_detector",
        input_data = event,
        output_data= detection,
        reasoning  = detection_raw,
        confidence = 1.0,
    )
    print(f"[AG1] Detection result: {detection}")

    # ── Phase 2: Investigate ─────────────────────────────────────────────────

    print("\n[MANAGER] Phase 2: Investigation")
    ag2 = make_investigator()
    t2  = investigator_task(ag2, event, detection)
    investigation_raw = make_crew([ag2], [t2]).kickoff().raw
    investigation     = _safe_parse(investigation_raw)

    # Safe defaults for investigation
    investigation.setdefault("root_cause",         "Unknown — investigation inconclusive")
    investigation.setdefault("confidence",          0.5)
    investigation.setdefault("evidence_sources",    [])
    investigation.setdefault("recommended_action",  "escalate")

    _log_decision(
        event_id   = event["event_id"],
        agent_name = "ag2_investigator",
        input_data = {**event, **detection},
        output_data= investigation,
        reasoning  = investigation_raw,
        confidence = investigation["confidence"],
    )
    print(f"[AG2] Investigation result: {investigation}")

    # ── First-principles fallback (code-enforced) ──────────────────────────
    # If evidence is weak, re-run Ag2 in explicit first-principles mode
    evidence = investigation.get("evidence_sources", [])
    conf = _safe_float(investigation.get("confidence", 0), 0.0)
    weak_evidence = (
        len(evidence) == 0
        or (len(evidence) == 1 and evidence[0] == "metrics")
        or conf < 0.4
    )

    if weak_evidence:
        print(f"\n[MANAGER] ⚡ Weak evidence detected (sources={evidence}, confidence={conf})")
        print(f"[MANAGER] Re-running Ag2 in FIRST_PRINCIPLES mode...")

        from agents.ag2_investigator import make_investigator as _make_inv
        from crewai import Task as _Task

        fp_agent = _make_inv()
        service = event["service"]
        anomaly = event["anomaly_type"]
        fp_task = _Task(
            description=f"""
You are in FIRST_PRINCIPLES mode. Prior investigation found weak evidence.

=== INCIDENT ===
Service: {service}
Anomaly: {anomaly}
Severity: {detection.get('severity', 'P3')}
Prior root cause guess: {investigation.get('root_cause', 'unknown')}
Prior confidence: {conf}

=== INSTRUCTIONS ===
Ignore RAG context. Reason purely from raw data:

1. Query live metrics:
   Use tool: query_snowflake
   SQL: SELECT metric_name, current_value, baseline_avg, z_score FROM ANALYTICS.METRIC_DEVIATIONS WHERE service_name = '{service}' ORDER BY ABS(z_score) DESC LIMIT 10

2. Query correlated services:
   Use tool: query_snowflake
   SQL: SELECT d.depends_on, md.metric_name, md.z_score FROM RAW.SERVICE_DEPENDENCIES d LEFT JOIN ANALYTICS.METRIC_DEVIATIONS md ON d.depends_on = md.service_name WHERE d.service_name = '{service}'

3. Reason from first principles:
   - What failure modes produce this metric pattern?
   - Are upstream/downstream services also affected?
   - Is this a deploy regression, infrastructure issue, or dependency failure?
   - What is the simplest explanation consistent with the data?

=== OUTPUT FORMAT ===
Return ONLY JSON:
{{"root_cause": "first-principles analysis of the cause", "confidence": 0.50-0.65, "evidence_sources": ["first_principles", "metrics"], "recommended_action": "rollback|fix_config|restart|scale_up|escalate", "mode": "FIRST_PRINCIPLES"}}
""",
            agent=fp_agent,
            expected_output='Valid JSON with keys: root_cause, confidence, evidence_sources, recommended_action, mode',
        )

        fp_raw = make_crew([fp_agent], [fp_task]).kickoff().raw
        fp_result = _safe_parse(fp_raw)

        if "error" not in fp_result and fp_result.get("root_cause"):
            fp_result.setdefault("confidence", 0.55)
            fp_result.setdefault("evidence_sources", ["first_principles", "metrics"])
            fp_result.setdefault("recommended_action", "escalate")
            fp_result["mode"] = "FIRST_PRINCIPLES"
            investigation = fp_result

            _log_decision(
                event_id   = event["event_id"],
                agent_name = "ag2_first_principles",
                input_data = {**event, **detection},
                output_data= investigation,
                reasoning  = fp_raw,
                confidence = investigation["confidence"],
            )
            print(f"[AG2-FP] First-principles result: {investigation}")
        else:
            print(f"[AG2-FP] First-principles re-run failed, keeping original investigation")
            # If even first-principles fails and confidence is very low, force escalation
            if conf < 0.4:
                investigation["recommended_action"] = "escalate"
                print(f"[AG2-FP] Forced recommended_action=escalate (confidence={conf})")

    ts_investigated = datetime.now(timezone.utc)

    # ── Phase 3: Validate + Debate loop ──────────────────────────────────────

    print("\n[MANAGER] Phase 3: Validation")
    debate_round = 0
    approved     = False

    while debate_round < MAX_DEBATE_ROUNDS and not approved:
        print(f"[MANAGER] Validation round {debate_round + 1}/{MAX_DEBATE_ROUNDS}")

        ag5 = make_validator()
        t5  = validator_task(ag5, investigation, event)
        validation_raw = make_crew([ag5], [t5]).kickoff().raw
        validation     = _safe_parse(validation_raw)

        validation.setdefault("verdict",              "DEBATE")
        validation.setdefault("confidence_adjustment", -0.05)
        validation.setdefault("objections",            [])
        validation.setdefault("notes",                 "")

        _log_decision(
            event_id   = event["event_id"],
            agent_name = "ag5_validator",
            input_data = investigation,
            output_data= validation,
            reasoning  = validation_raw,
            confidence = investigation["confidence"],
        )
        print(f"[AG5] Validation result: {validation}")

        if validation["verdict"] == "APPROVED":
            approved = True
            # Apply positive confidence adjustment on approval
            conf = _safe_float(investigation["confidence"], 0.5)
            adj = _safe_float(validation["confidence_adjustment"], 0.0)
            investigation["confidence"] = round(min(1.0, conf + adj), 4)
            print(f"[AG5] ✅ APPROVED — final confidence: {investigation['confidence']}")
        else:
            debate_round += 1
            # Reduce confidence on debate; investigator will retry next round
            conf = _safe_float(investigation["confidence"], 0.5)
            adj = _safe_float(validation["confidence_adjustment"], -0.05)
            investigation["confidence"] = round(max(0.0, conf + adj), 4)
            print(f"[AG5] ⚠️ DEBATE — objections: {validation['objections']}")
            print(f"[AG5] Adjusted confidence: {investigation['confidence']}")

            if debate_round < MAX_DEBATE_ROUNDS:
                # Re-run investigator with validator's objections as extra context
            
                print(f"\n[MANAGER] Re-running investigation with validator objections...")
                enriched_event = {
                    **event,
                    "validator_objections": validation["objections"],
                    "validator_notes":      validation["notes"],
                }
                ag2b = make_investigator()
                t2b  = investigator_task(ag2b, enriched_event, detection)
                reinvestigation_raw = make_crew([ag2b], [t2b]).kickoff().raw
                reinvestigation     = _safe_parse(reinvestigation_raw)

                # Update investigation only if re-run succeeded
                if "error" not in reinvestigation:
                    reinvestigation.setdefault("root_cause",         investigation["root_cause"])
                    reinvestigation.setdefault("confidence",          investigation["confidence"])
                    reinvestigation.setdefault("evidence_sources",    investigation["evidence_sources"])
                    reinvestigation.setdefault("recommended_action",  investigation["recommended_action"])
                    investigation = reinvestigation

                    _log_decision(
                        event_id   = event["event_id"],
                        agent_name = "ag2_investigator",
                        input_data = {**enriched_event, **detection},
                        output_data= investigation,
                        reasoning  = reinvestigation_raw,
                        confidence = investigation["confidence"],
                    )
                    print(f"[AG2] Re-investigation result: {investigation}")

    # After max rounds — proceed with best available answer
    if not approved:
        print(f"[MANAGER] Max debate rounds reached. Proceeding with confidence={investigation['confidence']}")

    # ── Phase 4: Fix Advisor (Ag3) ───────────────────────────────────────────
    print("\n[MANAGER] Phase 4: Fix Advisory")
    ag3 = make_fix_advisor()
    t3  = fix_advisor_task(ag3, event, investigation)
    fix_raw = make_crew([ag3], [t3]).kickoff().raw
    fix_result = _safe_parse(fix_raw)

    fix_options = fix_result.get("fix_options", [])
    if not fix_options:
        fix_options = [{"rank": 1, "title": investigation["recommended_action"], "commands": [], "estimated_time": "unknown", "risk_level": "MEDIUM", "rollback": "Revert deploy"}]

    _log_decision(
        event_id   = event["event_id"],
        agent_name = "ag3_fix_advisor",
        input_data = {**event, "investigation": investigation},
        output_data= fix_result,
        reasoning  = fix_raw,
        confidence = investigation["confidence"],
    )
    print(f"[AG3] Fix options: {len(fix_options)} generated")

    # ── Phase 4.5: Threshold Engine ──────────────────────────────────────────
    print("\n[MANAGER] Phase 4.5: Autonomous Resolution Threshold Engine")
    root_cause = investigation["root_cause"]
    fix        = investigation["recommended_action"]
    severity   = detection["severity"]
    blast_radius = detection.get("blast_radius", [])

    threshold = _evaluate_threshold(event, detection, investigation, fix_options, approved)
    print(f"[THRESHOLD] Decision: {threshold['decision']} (Rule: {threshold['rule_applied']})")
    print(f"[THRESHOLD] Type: {threshold['incident_type']} | Urgency: {threshold.get('urgency')}")
    print(f"[THRESHOLD] Confidence: {threshold['confidence']} | Risk: {threshold['risk_level']} | Fix proven: {threshold['fix_proven']}")

    _log_decision(
        event_id   = event["event_id"],
        agent_name = "threshold_engine",
        input_data = {"confidence": threshold["confidence"], "risk_level": threshold["risk_level"],
                       "fix_proven": threshold["fix_proven"], "blast_radius_count": threshold["blast_radius_count"],
                       "incident_type": threshold["incident_type"], "approved": approved},
        output_data= threshold,
        reasoning  = f"Rule {threshold['rule_applied']}: {threshold['rule_description']}",
        confidence = threshold["confidence"],
    )

    # ── Phase 5: Action Agent (Ag4) + Conditional Composio Actions ─────────
    print("\n[MANAGER] Phase 5: Actions")

    # Use Ag4 to compose action content
    ag4 = make_action_agent()
    t4  = action_task(ag4, event, detection, investigation, fix_options)
    action_raw = make_crew([ag4], [t4]).kickoff().raw
    action_content = _safe_parse(action_raw)

    _log_decision(
        event_id   = event["event_id"],
        agent_name = "ag4_action_agent",
        input_data = {**event, "detection": detection, "investigation": investigation},
        output_data= action_content,
        reasoning  = action_raw,
        confidence = investigation["confidence"],
    )

    # Compute MTTR for reporting
    ts_actions = datetime.now(timezone.utc)
    mttr_seconds = int((ts_actions - ts_detected).total_seconds())

    # Execute actions conditioned on threshold decision
    if threshold["decision"] == "AUTO_RESOLVE":
        print("[MANAGER] AUTO-RESOLVE path — executing fix + sending auto-resolved alerts")

        # DEMO_MODE: simulate fix execution and inject recovery metrics
        fix_cmd = fix_options[0].get("commands", ["rollback"])[0] if fix_options and fix_options[0].get("commands") else fix
        simulate_fix_execution(fix_cmd, event["service"])
        inject_recovery_metrics(event["service"], delay_seconds=2.0)

        slack_result = post_slack_alert_auto_resolved(
            event["event_id"], event["service"], severity, root_cause,
            blast_radius=blast_radius, fix_options=fix_options,
            confidence=threshold["confidence"], mttr_seconds=mttr_seconds,
        )
        github_result = create_github_issue(
            event["event_id"], event["service"], severity,
            root_cause, f"[AUTO-RESOLVED] {fix}",
        )
    else:
        print(f"[MANAGER] HUMAN_ESCALATION path — urgency={threshold.get('urgency')}")
        slack_result = post_slack_alert_escalation(
            event["event_id"], event["service"], severity, root_cause,
            blast_radius=blast_radius, fix_options=fix_options,
            urgency=threshold.get("urgency", "MEDIUM_CONFIDENCE"),
            incident_type=threshold["incident_type"],
            confidence=threshold["confidence"],
        )
        github_result = create_github_issue(
            event["event_id"], event["service"], severity, root_cause, fix,
        )

    print(f"[AG4] Slack  -> {slack_result}")
    print(f"[AG4] GitHub -> {github_result}")

    # Log manager's final decision
    _log_decision(
        event_id   = event["event_id"],
        agent_name = "manager",
        input_data = {**event, "investigation": investigation, "detection": detection,
                       "fix_options": fix_options, "threshold": threshold},
        output_data= {"slack": slack_result, "github": github_result, "approved": approved,
                       "fix_options": fix_options, "threshold_decision": threshold["decision"]},
        reasoning  = (f"Pipeline completed. Decision={threshold['decision']} via {threshold['rule_applied']}. "
                      f"Approved={approved}. Debate rounds={debate_round}. Fix options={len(fix_options)}."),
        confidence = investigation["confidence"],
    )

    # ── Phase 6: Store DNA ────────────────────────────────────────────────────
    print("\n[MANAGER] Phase 6: Storing incident DNA")
    ts_resolved = datetime.now(timezone.utc)
    mttr_minutes = int((ts_resolved - ts_detected).total_seconds() / 60)
    auto_fixed = threshold["decision"] == "AUTO_RESOLVE"
    incident_type = threshold["incident_type"]

    # Try extended schema first (with threshold columns), then fall back
    try:
        run_dml(
            """INSERT INTO AI.INCIDENT_HISTORY
                   (event_id, service_name, root_cause, fix_applied, confidence,
                    mttr_minutes, resolved_at, auto_fixed, incident_type,
                    threshold_decision, rule_applied)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                event["event_id"],
                event["service"],
                root_cause,
                fix,
                investigation["confidence"],
                mttr_minutes,
                ts_resolved.strftime("%Y-%m-%d %H:%M:%S"),
                auto_fixed,
                incident_type,
                threshold["decision"],
                threshold["rule_applied"],
            ),
        )
        print(f"[MANAGER] Incident DNA stored — MTTR={mttr_minutes}min | auto_fixed={auto_fixed} | {threshold['rule_applied']}")
    except Exception as e:
        print(f"[MANAGER] Extended schema insert failed, trying compact fallback: {e}")
        try:
            run_dml(
                """INSERT INTO AI.INCIDENT_HISTORY
                       (event_id, service_name, root_cause, fix_applied,
                        mttr_minutes, confidence, resolved_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    event["event_id"],
                    event["service"],
                    root_cause,
                    fix,
                    mttr_minutes,
                    investigation["confidence"],
                    ts_resolved.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            print(f"[MANAGER] Incident DNA stored via compact schema fallback — MTTR={mttr_minutes}min")
        except Exception as fallback_error:
            print(f"[MANAGER] Warning: failed to store DNA: {fallback_error}")

    result = {
        "event_id":           event["event_id"],
        "severity":           severity,
        "root_cause":         root_cause,
        "fix":                fix,
        "fix_options":        fix_options,
        "confidence":         investigation["confidence"],
        "approved":           approved,
        "debate_rounds":      debate_round,
        "blast_radius":       detection.get("blast_radius", []),
        "evidence":           investigation.get("evidence_sources", []),
        "slack":              slack_result,
        "github":             github_result,
        # Threshold engine fields
        "threshold_decision": threshold["decision"],
        "rule_applied":       threshold["rule_applied"],
        "rule_description":   threshold["rule_description"],
        "urgency":            threshold.get("urgency"),
        "incident_type":      threshold["incident_type"],
        "auto_fixed":         auto_fixed,
        "fix_proven":         threshold["fix_proven"],
        "risk_level":         threshold["risk_level"],
        "mttr_seconds":       mttr_seconds,
    }

    print(f"\n{'='*60}")
    print(f"[MANAGER] Pipeline complete — event_id={event['event_id']}")
    print(f"[MANAGER] Decision: {threshold['decision']} via {threshold['rule_applied']}")
    print(f"[MANAGER] Result: {result}")
    print(f"{'='*60}\n")

    return result
