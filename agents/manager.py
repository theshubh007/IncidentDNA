"""
IncidentDNA — Agent Manager
Orchestrates Ag1 → Ag2 → Ag5 (debate loop) → Actions → DNA storage.

Entry point: run_incident_crew(event: dict) -> dict
Called directly by ingestion/trigger_listener.py (no HTTP bridge).
"""

import json
import re
from agents.ag1_detector import make_detector, detector_task
from agents.ag2_investigator import make_investigator, investigator_task
from agents.ag5_validator import make_validator, validator_task
from agents.crew import make_crew
from tools.composio_actions import post_slack_alert, create_github_issue
from utils.snowflake_conn import run_dml

MAX_DEBATE_ROUNDS = 2


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
                   (event_id, agent_name, input, output, reasoning, confidence)
               VALUES (%s, %s, PARSE_JSON(%s), PARSE_JSON(%s), %s, %s)""",
            (
                event_id,
                agent_name,
                json.dumps(input_data),
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

    # ── Phase 4: Act ─────────────────────────────────────────────────────────
    print("\n[MANAGER] Phase 4: Actions")
    root_cause = investigation["root_cause"]
    fix        = investigation["recommended_action"]
    severity   = detection["severity"]

    slack_result  = post_slack_alert(event["event_id"], event["service"], severity, root_cause)
    github_result = create_github_issue(event["event_id"], event["service"], severity, root_cause, fix)

    print(f"[ACTIONS] Slack  → {slack_result}")
    print(f"[ACTIONS] GitHub → {github_result}")

    # Log manager's final decision
    _log_decision(
        event_id   = event["event_id"],
        agent_name = "manager",
        input_data = {**event, "investigation": investigation, "detection": detection},
        output_data= {"slack": slack_result, "github": github_result, "approved": approved},
        reasoning  = f"Pipeline completed. Approved={approved}. Debate rounds={debate_round}.",
        confidence = investigation["confidence"],
    )

    # ── Phase 5: Store DNA ────────────────────────────────────────────────────
    print("\n[MANAGER] Phase 5: Storing incident DNA")
    try:
        run_dml(
            """INSERT INTO AI.INCIDENT_HISTORY
                   (event_id, service, root_cause, fix_applied, severity, confidence, mttr_minutes)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                event["event_id"],
                event["service"],
                root_cause,
                fix,
                severity,
                investigation["confidence"],
                0,  # mttr updated externally once incident is truly resolved
            ),
        )
        print("[MANAGER] ✅ Incident DNA stored in AI.INCIDENT_HISTORY")
    except Exception as e:
        print(f"[MANAGER] Warning: failed to store DNA: {e}")

    result = {
        "event_id":     event["event_id"],
        "severity":     severity,
        "root_cause":   root_cause,
        "fix":          fix,
        "confidence":   investigation["confidence"],
        "approved":     approved,
        "debate_rounds": debate_round,
        "blast_radius": detection.get("blast_radius", []),
        "evidence":     investigation.get("evidence_sources", []),
        "slack":        slack_result,
        "github":       github_result,
    }

    print(f"\n{'='*60}")
    print(f"[MANAGER] Pipeline complete — event_id={event['event_id']}")
    print(f"[MANAGER] Result: {result}")
    print(f"{'='*60}\n")

    return result
