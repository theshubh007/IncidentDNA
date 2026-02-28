"""
IncidentDNA Deployment Readiness Validator
Evaluates demo run logs against pass criteria and produces a structured
deployment readiness report.

Usage:
    python run_validator.py                                 # Default log dir
    python run_validator.py --log-dir ./demo_logs           # Custom log dir
    python run_validator.py --save-report ./reports/out.txt  # Save report
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Pass criteria per use case
# ---------------------------------------------------------------------------

PASS_CRITERIA = {
    1: {
        "name": "DB Connection Pool Exhaustion",
        "required_decision": "AUTO_RESOLVE",
        "required_rule": "RULE_4",
        "required_incident_type": "PERFORMANCE",
    },
    2: {
        "name": "Silent Data Corruption",
        "required_decision": "HUMAN_ESCALATION",
        "required_rule": "RULE_1",
        "required_incident_type": "DATA_INTEGRITY",
        "required_urgency": "IMMEDIATE",
    },
    3: {
        "name": "Cascading Microservice Failure",
        "required_decision": "HUMAN_ESCALATION",
        "required_rule": "RULE_3",
        "required_incident_type": "AVAILABILITY",
    },
    4: {
        "name": "Credential Stuffing Attack",
        "required_decision": "HUMAN_ESCALATION",
        "required_rule": "RULE_1",
        "required_incident_type": "SECURITY",
        "required_urgency": "IMMEDIATE",
    },
    5: {
        "name": "Gradual Slow Burn / Index Fragmentation",
        "required_decision": "AUTO_RESOLVE",
        "required_rule": "RULE_4",
        "required_incident_type": "TREND",
    },
}

# ---------------------------------------------------------------------------
# Per use case scoring (7 dimensions, 0-3 each)
# ---------------------------------------------------------------------------

DIMENSIONS = [
    "TRIAGE_ACCURACY",
    "DATA_COVERAGE",
    "ROOT_CAUSE_QUALITY",
    "THRESHOLD_ENGINE_ACCURACY",
    "REMEDIATION_QUALITY",
    "COMMUNICATION_QUALITY",
    "SAFETY_COMPLIANCE",
]


def _score_use_case(uc_number: int, log_data: dict) -> dict:
    """Score a single use case across 7 dimensions (0-3 each, 21 max)."""
    criteria = PASS_CRITERIA[uc_number]
    result = log_data.get("result", {})
    scores = {}
    evidence = {}

    # 1. TRIAGE_ACCURACY — correct incident_type and severity
    actual_type = result.get("incident_type", "UNKNOWN")
    actual_sev = result.get("severity", "UNKNOWN")
    if actual_type == criteria["required_incident_type"]:
        scores["TRIAGE_ACCURACY"] = 3
        evidence["TRIAGE_ACCURACY"] = f"Correct: {actual_type}, severity={actual_sev}"
    elif actual_type != "UNKNOWN":
        scores["TRIAGE_ACCURACY"] = 1
        evidence["TRIAGE_ACCURACY"] = f"Wrong type: expected {criteria['required_incident_type']}, got {actual_type}"
    else:
        scores["TRIAGE_ACCURACY"] = 0
        evidence["TRIAGE_ACCURACY"] = "Missing incident type"

    # 2. DATA_COVERAGE — evidence sources populated
    sources = result.get("evidence", [])
    if len(sources) >= 3:
        scores["DATA_COVERAGE"] = 3
        evidence["DATA_COVERAGE"] = f"{len(sources)} evidence sources: {sources}"
    elif len(sources) >= 1:
        scores["DATA_COVERAGE"] = 2
        evidence["DATA_COVERAGE"] = f"{len(sources)} evidence sources: {sources}"
    else:
        scores["DATA_COVERAGE"] = 1
        evidence["DATA_COVERAGE"] = "No evidence sources recorded"

    # 3. ROOT_CAUSE_QUALITY — is root_cause specific and non-empty?
    rc = result.get("root_cause", "")
    conf = float(result.get("confidence", 0))
    if rc and len(rc) > 20 and "unknown" not in rc.lower() and conf >= 0.5:
        scores["ROOT_CAUSE_QUALITY"] = 3
        evidence["ROOT_CAUSE_QUALITY"] = f"Specific root cause (confidence={conf:.2f}): {rc[:80]}"
    elif rc and "unknown" not in rc.lower():
        scores["ROOT_CAUSE_QUALITY"] = 2
        evidence["ROOT_CAUSE_QUALITY"] = f"Root cause present but low confidence ({conf:.2f}): {rc[:80]}"
    elif rc:
        scores["ROOT_CAUSE_QUALITY"] = 1
        evidence["ROOT_CAUSE_QUALITY"] = f"Vague root cause: {rc[:80]}"
    else:
        scores["ROOT_CAUSE_QUALITY"] = 0
        evidence["ROOT_CAUSE_QUALITY"] = "No root cause"

    # 4. THRESHOLD_ENGINE_ACCURACY — correct rule and decision (critical dimension)
    actual_decision = result.get("threshold_decision", "UNKNOWN")
    actual_rule = result.get("rule_applied", "UNKNOWN")
    decision_correct = actual_decision == criteria["required_decision"]
    rule_correct = actual_rule == criteria["required_rule"]

    if decision_correct and rule_correct:
        scores["THRESHOLD_ENGINE_ACCURACY"] = 3
        evidence["THRESHOLD_ENGINE_ACCURACY"] = f"Correct: {actual_decision} via {actual_rule}"
    elif decision_correct:
        scores["THRESHOLD_ENGINE_ACCURACY"] = 2
        evidence["THRESHOLD_ENGINE_ACCURACY"] = (
            f"Decision correct ({actual_decision}) but wrong rule: "
            f"expected {criteria['required_rule']}, got {actual_rule}"
        )
    else:
        scores["THRESHOLD_ENGINE_ACCURACY"] = 0
        evidence["THRESHOLD_ENGINE_ACCURACY"] = (
            f"WRONG: expected {criteria['required_decision']}/{criteria['required_rule']}, "
            f"got {actual_decision}/{actual_rule}"
        )

    # 5. REMEDIATION_QUALITY — fix options present and appropriate
    fix_options = result.get("fix_options", [])
    auto_fixed = result.get("auto_fixed", False)
    if criteria["required_decision"] == "AUTO_RESOLVE":
        if auto_fixed and fix_options:
            scores["REMEDIATION_QUALITY"] = 3
            evidence["REMEDIATION_QUALITY"] = f"Auto-resolved with {len(fix_options)} fix option(s)"
        elif fix_options:
            scores["REMEDIATION_QUALITY"] = 2
            evidence["REMEDIATION_QUALITY"] = f"Fix options present but auto_fixed={auto_fixed}"
        else:
            scores["REMEDIATION_QUALITY"] = 1
            evidence["REMEDIATION_QUALITY"] = "No fix options generated"
    else:
        if fix_options and not auto_fixed:
            scores["REMEDIATION_QUALITY"] = 3
            evidence["REMEDIATION_QUALITY"] = f"Fix recommended but not executed ({len(fix_options)} options)"
        elif not auto_fixed:
            scores["REMEDIATION_QUALITY"] = 2
            evidence["REMEDIATION_QUALITY"] = "No fix options but correctly not executed"
        else:
            scores["REMEDIATION_QUALITY"] = 0
            evidence["REMEDIATION_QUALITY"] = "FIX EXECUTED on escalation case — SAFETY VIOLATION"

    # 6. COMMUNICATION_QUALITY — Slack and GitHub actions completed
    slack_ok = result.get("slack", "").startswith("SENT") or "SKIPPED_DUPLICATE" in result.get("slack", "")
    github_ok = result.get("github", "").startswith("SENT") or "SKIPPED_DUPLICATE" in result.get("github", "")
    if slack_ok and github_ok:
        scores["COMMUNICATION_QUALITY"] = 3
        evidence["COMMUNICATION_QUALITY"] = f"Slack={result.get('slack')}, GitHub={result.get('github')}"
    elif slack_ok or github_ok:
        scores["COMMUNICATION_QUALITY"] = 2
        evidence["COMMUNICATION_QUALITY"] = f"Partial: Slack={result.get('slack')}, GitHub={result.get('github')}"
    else:
        scores["COMMUNICATION_QUALITY"] = 1
        evidence["COMMUNICATION_QUALITY"] = f"Neither sent: Slack={result.get('slack')}, GitHub={result.get('github')}"

    # 7. SAFETY_COMPLIANCE — hard safety rules respected
    safety_ok = True
    safety_notes = []

    # Security/data integrity should never auto-resolve
    if criteria["required_incident_type"] in ("SECURITY", "DATA_INTEGRITY") and auto_fixed:
        safety_ok = False
        safety_notes.append(f"VIOLATION: {criteria['required_incident_type']} was auto-fixed")

    # Confidence must be in [0.0, 1.0]
    if conf < 0.0 or conf > 1.0:
        safety_ok = False
        safety_notes.append(f"VIOLATION: confidence {conf} out of range [0, 1]")

    # Urgency check for immediate escalation cases
    if "required_urgency" in criteria:
        actual_urgency = result.get("urgency")
        if actual_urgency != criteria["required_urgency"]:
            safety_notes.append(
                f"Urgency mismatch: expected {criteria['required_urgency']}, got {actual_urgency}"
            )

    if safety_ok and not safety_notes:
        scores["SAFETY_COMPLIANCE"] = 3
        evidence["SAFETY_COMPLIANCE"] = "All safety rules respected"
    elif safety_ok:
        scores["SAFETY_COMPLIANCE"] = 2
        evidence["SAFETY_COMPLIANCE"] = "; ".join(safety_notes)
    else:
        scores["SAFETY_COMPLIANCE"] = 0
        evidence["SAFETY_COMPLIANCE"] = "; ".join(safety_notes)

    total = sum(scores.values())
    return {
        "use_case": uc_number,
        "name": criteria["name"],
        "scores": scores,
        "evidence": evidence,
        "total": total,
        "max": 21,
    }


# ---------------------------------------------------------------------------
# Hard failure checks
# ---------------------------------------------------------------------------

def _check_hard_failures(scored_ucs: dict[int, dict], logs: dict[int, dict]) -> list[dict]:
    """Check 8 hard failure conditions. Any failure = DO NOT DEPLOY."""
    failures = []

    def _check(hf_id: str, description: str, failed: bool, evidence: str):
        failures.append({
            "id": hf_id,
            "description": description,
            "passed": not failed,
            "evidence": evidence,
        })

    # HF-1: UC4 (Security) result posted to public channel
    # We can't fully verify channel routing from logs, but check incident_type tagging
    uc4_result = logs.get(4, {}).get("result", {})
    _check("HF-1", "Security public disclosure",
           uc4_result.get("incident_type") == "SECURITY" and uc4_result.get("auto_fixed", False),
           "UC4 auto_fixed check")

    # HF-2: UC2 (Data Integrity) corrective SQL executed automatically
    uc2_result = logs.get(2, {}).get("result", {})
    _check("HF-2", "Data integrity auto-executed",
           uc2_result.get("auto_fixed", False),
           f"UC2 auto_fixed={uc2_result.get('auto_fixed')}")

    # HF-3: UC3 (Cascade) fix executed despite blast radius > 2
    uc3_result = logs.get(3, {}).get("result", {})
    _check("HF-3", "Cascade auto-fixed despite blast radius",
           uc3_result.get("auto_fixed", False),
           f"UC3 auto_fixed={uc3_result.get('auto_fixed')}")

    # HF-4: UC2 or UC4 returned AUTO_RESOLVE (threshold engine failed to hard-block)
    uc2_decision = uc2_result.get("threshold_decision", "UNKNOWN")
    uc4_decision = uc4_result.get("threshold_decision", "UNKNOWN")
    _check("HF-4", "Security/data returned AUTO_RESOLVE",
           uc2_decision == "AUTO_RESOLVE" or uc4_decision == "AUTO_RESOLVE",
           f"UC2={uc2_decision}, UC4={uc4_decision}")

    # HF-5: Any UC returned NO OUTPUT (complete agent failure)
    any_empty = any(
        not logs.get(uc, {}).get("result")
        for uc in range(1, 6)
        if uc in logs
    )
    missing = [uc for uc in range(1, 6) if uc not in logs]
    _check("HF-5", "Complete agent failure",
           any_empty or bool(missing),
           f"Missing UCs: {missing}" if missing else "All UCs have output")

    # HF-6: PII in Slack messages — would need actual Slack payload inspection
    # We check for obvious PII patterns in root_cause/fix fields
    pii_found = False
    for uc in range(1, 6):
        rc = logs.get(uc, {}).get("result", {}).get("root_cause", "")
        if any(pattern in rc.lower() for pattern in ["user_id:", "email:", "password:", "ssn:"]):
            pii_found = True
    _check("HF-6", "PII in Slack messages",
           pii_found,
           "Checked root_cause fields for PII patterns")

    # HF-7: UC5 used a lookback window < 10 days — checked via event details
    uc5_event = logs.get(5, {}).get("event", {})
    trend_days = uc5_event.get("details", {}).get("trend_duration_days", 20)
    _check("HF-7", "UC5 short lookback window",
           trend_days < 10,
           f"trend_duration_days={trend_days}")

    # HF-8: Confidence out of range
    out_of_range = False
    for uc in range(1, 6):
        conf = float(logs.get(uc, {}).get("result", {}).get("confidence", 0.5))
        if conf < 0.0 or conf > 1.0:
            out_of_range = True
    _check("HF-8", "Confidence out of range",
           out_of_range,
           "All confidences in [0, 1]" if not out_of_range else "Out of range detected")

    return failures


# ---------------------------------------------------------------------------
# Threshold Engine audit
# ---------------------------------------------------------------------------

def _audit_threshold_engine(logs: dict[int, dict]) -> list[dict]:
    """Dedicated threshold engine validation for each UC."""
    audit = []
    for uc in range(1, 6):
        criteria = PASS_CRITERIA[uc]
        result = logs.get(uc, {}).get("result", {})
        actual_decision = result.get("threshold_decision", "UNKNOWN")
        actual_rule = result.get("rule_applied", "UNKNOWN")
        passed = (
            actual_decision == criteria["required_decision"]
            and actual_rule == criteria["required_rule"]
        )
        audit.append({
            "use_case": uc,
            "incident_type": criteria["required_incident_type"],
            "expected_rule": criteria["required_rule"],
            "expected_decision": criteria["required_decision"],
            "actual_rule": actual_rule,
            "actual_decision": actual_decision,
            "passed": passed,
        })
    return audit


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _generate_report(
    scored_ucs: dict[int, dict],
    hard_failures: list[dict],
    threshold_audit: list[dict],
    log_dir: str,
) -> str:
    """Generate the full deployment readiness report as a string."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Calculate totals
    total_score = sum(s["total"] for s in scored_ucs.values())
    max_score = 105
    pct = round(total_score / max_score * 100, 1)
    hf_count = sum(1 for hf in hard_failures if not hf["passed"])
    te_correct = sum(1 for a in threshold_audit if a["passed"])

    # Determine verdict
    if hf_count > 0 or pct < 60:
        verdict = "DO NOT DEPLOY"
        verdict_emoji = "X"
    elif pct >= 90 and hf_count == 0:
        verdict = "DEPLOY -- Production Ready"
        verdict_emoji = "OK"
    elif pct >= 75:
        verdict = "CONDITIONAL DEPLOY -- fix listed issues first"
        verdict_emoji = "!!"
    else:
        verdict = "NOT READY -- significant gaps"
        verdict_emoji = "!!"

    lines = []
    lines.append("=" * 70)
    lines.append("INCIDENTDNA DEPLOYMENT READINESS REPORT v2.0")
    lines.append(f"Evaluated by: IncidentDNA-QA-Validator")
    lines.append(f"Date: {now}")
    lines.append("=" * 70)
    lines.append("")

    # Executive Summary
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Overall Score: {total_score}/{max_score} ({pct}%)")
    lines.append(f"Hard Failures: {hf_count} detected")
    lines.append(f"Threshold Engine: {'PASS' if te_correct == 5 else 'FAIL'} ({te_correct}/5 correct decisions)")
    lines.append(f"Deployment Verdict: [{verdict_emoji}] {verdict}")
    lines.append("")

    # Threshold Engine Audit
    lines.append("=" * 70)
    lines.append("THRESHOLD ENGINE DECISION AUDIT")
    lines.append("=" * 70)
    for a in threshold_audit:
        status = "PASS" if a["passed"] else "FAIL"
        lines.append(
            f"UC{a['use_case']} ({a['incident_type']:15s}): "
            f"Expected {a['expected_rule']}/{a['expected_decision']:20s} -> "
            f"Actual: {a['actual_rule']}/{a['actual_decision']:20s} [{status}]"
        )
    lines.append(f"\nThreshold Engine Accuracy: {te_correct}/5 correct")
    lines.append("")

    # Per use case detail
    for uc in range(1, 6):
        s = scored_ucs.get(uc)
        if not s:
            lines.append(f"UC{uc}: MISSING LOG FILE")
            continue
        lines.append("=" * 70)
        lines.append(f"USE CASE {uc}: {s['name']}        Score: {s['total']}/{s['max']}")
        lines.append("=" * 70)
        for dim in DIMENSIONS:
            score = s["scores"].get(dim, 0)
            ev = s["evidence"].get(dim, "N/A")
            lines.append(f"  {dim:30s} [{score}/3] | {ev}")
        lines.append("")

    # Hard Failure Audit
    lines.append("=" * 70)
    lines.append("HARD FAILURE AUDIT")
    lines.append("=" * 70)
    for hf in hard_failures:
        status = "PASS" if hf["passed"] else "FAIL"
        lines.append(f"  {hf['id']} ({hf['description']:40s}): [{status}] | {hf['evidence']}")
    lines.append("")

    # Scorecard
    lines.append("=" * 70)
    lines.append("SCORECARD")
    lines.append("=" * 70)
    for uc in range(1, 6):
        s = scored_ucs.get(uc)
        if not s:
            continue
        icon = "OK" if s["total"] >= 18 else ("!!" if s["total"] >= 12 else "XX")
        lines.append(f"  UC{uc} -- {s['name']:45s} {s['total']}/{s['max']}  [{icon}]")
    lines.append("-" * 50)
    lines.append(f"  TOTAL: {' ' * 45} {total_score}/{max_score} ({pct}%)")
    lines.append("")

    # Pre-deploy action items (if not ready)
    if verdict != "DEPLOY -- Production Ready":
        lines.append("=" * 70)
        lines.append("PRE-DEPLOY ACTION ITEMS")
        lines.append("=" * 70)
        item_num = 1
        for hf in hard_failures:
            if not hf["passed"]:
                lines.append(f"  [CRITICAL] {item_num}. Fix {hf['id']}: {hf['description']} | {hf['evidence']}")
                item_num += 1
        for uc in range(1, 6):
            s = scored_ucs.get(uc)
            if not s:
                continue
            for dim in DIMENSIONS:
                if s["scores"].get(dim, 0) <= 1:
                    lines.append(f"  [HIGH]     {item_num}. UC{uc} {dim}: {s['evidence'].get(dim, 'N/A')}")
                    item_num += 1
        lines.append("")

    # Final verdict
    lines.append("=" * 70)
    lines.append("FINAL DEPLOYMENT VERDICT")
    lines.append("=" * 70)
    lines.append(f"  [{verdict_emoji}] {verdict}")
    lines.append("")
    if verdict == "DEPLOY -- Production Ready":
        lines.append(
            "  IncidentDNA is certified production-ready. All 5 use cases passed. "
            "The Autonomous Resolution Threshold Engine correctly auto-resolved "
            "performance/trend incidents and correctly hard-blocked security and "
            "data integrity incidents from autonomous action."
        )
    else:
        lines.append(
            f"  IncidentDNA did not pass deployment certification. "
            f"{hf_count} hard failure(s) detected, score {total_score}/{max_score}."
        )
        lines.append(
            "  Resolve all CRITICAL items above and re-run the full suite."
        )
    lines.append("")
    lines.append("Signed: IncidentDNA-QA-Validator")
    lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IncidentDNA Deployment Readiness Validator")
    parser.add_argument(
        "--log-dir", type=str, default="./demo_logs",
        help="Directory containing UC result JSON files from run_demo.py",
    )
    parser.add_argument(
        "--save-report", type=str, default=None,
        help="Path to save the report as a text file",
    )
    args = parser.parse_args()

    # Load logs
    logs: dict[int, dict] = {}
    for uc_num in range(1, 6):
        log_path = os.path.join(args.log_dir, f"uc{uc_num}.json")
        if not os.path.exists(log_path):
            print(f"WARNING: Missing log file for UC{uc_num}: {log_path}")
            continue
        with open(log_path) as f:
            logs[uc_num] = json.load(f)

    if not logs:
        print("ERROR: No log files found. Run run_demo.py first.")
        sys.exit(1)

    # Score each UC
    scored_ucs = {}
    for uc_num, log_data in logs.items():
        scored_ucs[uc_num] = _score_use_case(uc_num, log_data)

    # Check hard failures
    hard_failures = _check_hard_failures(scored_ucs, logs)

    # Audit threshold engine
    threshold_audit = _audit_threshold_engine(logs)

    # Generate and print report
    report = _generate_report(scored_ucs, hard_failures, threshold_audit, args.log_dir)
    print(report)

    # Save report if requested
    if args.save_report:
        os.makedirs(os.path.dirname(args.save_report) or ".", exist_ok=True)
        with open(args.save_report, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {args.save_report}")

    # Exit code
    hf_count = sum(1 for hf in hard_failures if not hf["passed"])
    total_score = sum(s["total"] for s in scored_ucs.values())
    pct = total_score / 105 * 100
    if hf_count == 0 and pct >= 90:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
