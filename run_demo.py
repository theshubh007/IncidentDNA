"""
IncidentDNA Demo Runner
Runs 5 use cases through the full pipeline to demonstrate the Autonomous
Resolution Threshold Engine.

Usage:
    python run_demo.py                          # Run all 5 use cases
    python run_demo.py --use-case 1             # Run specific use case (1-5)
    python run_demo.py --save-log ./demo_logs   # Save JSON logs to directory
    python run_demo.py --use-case 1 --save-log ./demo_logs
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Enable auto-fix and demo mode for the threshold engine
os.environ["AUTO_FIX_ENABLED"] = "true"
os.environ["DEMO_MODE"] = "true"
# Whitelist all demo services for auto-fix
os.environ.setdefault("AUTO_FIX_WHITELIST", "payment-service,worker-service")

# ---------------------------------------------------------------------------
# Use case definitions
# ---------------------------------------------------------------------------

def _make_event_id(uc: int) -> str:
    return f"demo-uc{uc}-{uuid.uuid4().hex[:8]}"


USE_CASES = {
    1: {
        "name": "DB Connection Pool Exhaustion",
        "expected_decision": "AUTO_RESOLVE",
        "expected_rule": "RULE_4",
        "event": lambda: {
            "event_id": _make_event_id(1),
            "service": "payment-service",
            "anomaly_type": "db_pool_exhaustion",
            "incident_type": "PERFORMANCE",
            "severity": "P1",
            "details": {
                "deploy_id": "DPL-20241129-0042",
                "metric_spike": "connection_pool_usage",
                "current_value": 48,
                "baseline": 20,
                "source": "demo_runner",
                # Threshold overrides for deterministic demo
                "confidence_override": 0.93,
                "approved_override": True,
                "blast_radius_override": 2,
                "fix_proven_override": True,
                "risk_level_override": "LOW",
            },
        },
    },
    2: {
        "name": "Silent Data Corruption",
        "expected_decision": "HUMAN_ESCALATION",
        "expected_rule": "RULE_1",
        "event": lambda: {
            "event_id": _make_event_id(2),
            "service": "order-service",
            "anomaly_type": "silent_data_corruption",
            "incident_type": "DATA_INTEGRITY",
            "severity": "P1",
            "details": {
                "deploy_id": "DPL-20241126-0019",
                "affected_records": 48302,
                "revenue_impact_pct": 10,
                "date_range": "Nov 26-29",
                "source": "demo_runner",
            },
        },
    },
    3: {
        "name": "Cascading Microservice Failure",
        "expected_decision": "HUMAN_ESCALATION",
        "expected_rule": "RULE_3",
        "event": lambda: {
            "event_id": _make_event_id(3),
            "service": "api-gateway",
            "anomaly_type": "cascading_failure",
            "incident_type": "AVAILABILITY",
            "severity": "P1",
            "details": {
                "deploy_id": "DPL-20241210-0091",
                "cascade_depth": 3,
                "affected_services": [
                    "payment-service", "order-service", "notification-service",
                    "product-service", "worker-service", "api-gateway", "search-service",
                ],
                "origin_service": "nlp-enrichment-svc",
                "source": "demo_runner",
                # Threshold overrides: ensure RULE 3 fires (blast_radius > 2)
                # approved_override=True prevents RULE 2 from firing first
                "approved_override": True,
                "blast_radius_override": 7,
            },
        },
    },
    4: {
        "name": "Credential Stuffing Attack",
        "expected_decision": "HUMAN_ESCALATION",
        "expected_rule": "RULE_1",
        "event": lambda: {
            "event_id": _make_event_id(4),
            "service": "user-service",
            "anomaly_type": "credential_stuffing",
            "incident_type": "SECURITY",
            "severity": "P1",
            "details": {
                "deploy_id": "DPL-20241215-SEC-0003",
                "failed_auth_attempts": 48291,
                "unique_ips": 11402,
                "success_rate_pct": 2.1,
                "potentially_compromised": 1014,
                "source": "demo_runner",
            },
        },
    },
    5: {
        "name": "Gradual Slow Burn / Index Fragmentation",
        "expected_decision": "AUTO_RESOLVE",
        "expected_rule": "RULE_4",
        "event": lambda: {
            "event_id": _make_event_id(5),
            "service": "worker-service",
            "anomaly_type": "gradual_degradation",
            "incident_type": "TREND",
            "severity": "P3",
            "details": {
                "deploy_id": "DPL-20241220-TREND-0001",
                "trend_duration_days": 20,
                "metric": "response_time_p99",
                "start_value_ms": 180,
                "current_value_ms": 208,
                "drift_pct": 15.5,
                "source": "demo_runner",
                # Threshold overrides for deterministic demo
                "confidence_override": 0.91,
                "approved_override": True,
                "blast_radius_override": 1,
                "fix_proven_override": True,
                "risk_level_override": "LOW",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Pre-seeding — ensure AI.INCIDENT_HISTORY has proven fixes for UC1 & UC5
# ---------------------------------------------------------------------------

def _seed_proven_fixes():
    """
    Insert historical incident records so fix_proven=True for UC1 and UC5.
    Idempotent — checks for existing records before inserting.
    """
    from utils.snowflake_conn import run_dml, run_query

    seeds = [
        {
            "event_id": "historical-db-pool-001",
            "service_name": "payment-service",
            "root_cause": "DB connection pool exhausted — max connections reached",
            "fix_applied": "scale_up",
            "confidence": 0.92,
            "mttr_minutes": 5,
        },
        {
            "event_id": "historical-slow-burn-001",
            "service_name": "worker-service",
            "root_cause": "Gradual degradation due to index fragmentation",
            "fix_applied": "rebuild_index",
            "confidence": 0.88,
            "mttr_minutes": 15,
        },
    ]

    for seed in seeds:
        try:
            existing = run_query(
                "SELECT COUNT(*) AS cnt FROM AI.INCIDENT_HISTORY WHERE event_id = %s",
                (seed["event_id"],),
            )
            if existing and existing[0]["CNT"] > 0:
                continue
            run_dml(
                """INSERT INTO AI.INCIDENT_HISTORY
                       (event_id, service_name, root_cause, fix_applied,
                        confidence, mttr_minutes, resolved_at)
                   VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())""",
                (
                    seed["event_id"],
                    seed["service_name"],
                    seed["root_cause"],
                    seed["fix_applied"],
                    seed["confidence"],
                    seed["mttr_minutes"],
                ),
            )
            print(f"[SEED] Inserted proven fix: {seed['event_id']}")
        except Exception as e:
            print(f"[SEED] Warning: could not seed {seed['event_id']}: {e}")


def _run_schema_migration():
    """Attempt to add threshold columns to AI.INCIDENT_HISTORY."""
    from utils.snowflake_conn import run_dml

    migrations = [
        "ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS auto_fixed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS incident_type VARCHAR DEFAULT 'PERFORMANCE'",
        "ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS threshold_decision VARCHAR",
        "ALTER TABLE AI.INCIDENT_HISTORY ADD COLUMN IF NOT EXISTS rule_applied VARCHAR",
    ]
    for sql in migrations:
        try:
            run_dml(sql)
        except Exception as e:
            print(f"[MIGRATION] Warning: {e}")


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_use_case(uc_number: int, save_dir: str | None = None) -> dict:
    """Run a single use case and return the result."""
    uc = USE_CASES[uc_number]
    event = uc["event"]()  # generate fresh event with unique ID

    print(f"\n{'='*70}")
    print(f"  USE CASE {uc_number}: {uc['name']}")
    print(f"  Expected: {uc['expected_decision']} via {uc['expected_rule']}")
    print(f"  Event ID: {event['event_id']}")
    print(f"{'='*70}\n")

    from agents.manager import run_incident_crew

    start = datetime.now(timezone.utc)
    result = run_incident_crew(event)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    actual_decision = result.get("threshold_decision", "UNKNOWN")
    actual_rule = result.get("rule_applied", "UNKNOWN")
    passed = (
        actual_decision == uc["expected_decision"]
        and actual_rule == uc["expected_rule"]
    )

    log_entry = {
        "use_case": uc_number,
        "name": uc["name"],
        "expected_decision": uc["expected_decision"],
        "expected_rule": uc["expected_rule"],
        "actual_decision": actual_decision,
        "actual_rule": actual_rule,
        "passed": passed,
        "elapsed_seconds": round(elapsed, 2),
        "event": event,
        "result": result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Print summary
    status = "PASS" if passed else "FAIL"
    print(f"\n{'='*70}")
    print(f"  [UC{uc_number}] {status}: {uc['name']}")
    print(f"  Expected: {uc['expected_decision']} / {uc['expected_rule']}")
    print(f"  Actual:   {actual_decision} / {actual_rule}")
    print(f"  Elapsed:  {elapsed:.1f}s")
    print(f"{'='*70}\n")

    # Save log if requested
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        log_path = os.path.join(save_dir, f"uc{uc_number}.json")
        with open(log_path, "w") as f:
            json.dump(log_entry, f, indent=2, default=str)
        print(f"  Log saved: {log_path}")

    return log_entry


def main():
    parser = argparse.ArgumentParser(description="IncidentDNA Demo Runner")
    parser.add_argument(
        "--use-case", type=int, choices=[1, 2, 3, 4, 5],
        help="Run a specific use case (1-5). Default: run all",
    )
    parser.add_argument(
        "--save-log", type=str, default="./demo_logs",
        help="Directory to save JSON log files (default: ./demo_logs)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("  IncidentDNA Demo Runner v2.0")
    print("  Autonomous Resolution Threshold Engine")
    print("=" * 70)

    # Pre-flight
    print("\n[SETUP] Running schema migration...")
    _run_schema_migration()
    print("[SETUP] Seeding proven fixes for auto-resolve use cases...")
    _seed_proven_fixes()

    if args.use_case:
        run_use_case(args.use_case, args.save_log)
    else:
        results = []
        for uc in range(1, 6):
            results.append(run_use_case(uc, args.save_log))

        # Print summary table
        print(f"\n{'='*70}")
        print("  DEMO SUMMARY")
        print(f"{'='*70}")
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            print(f"  UC{r['use_case']}: [{status}] {r['name']}")
            print(f"         Decision: {r['actual_decision']} / {r['actual_rule']}")
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        print(f"\n  Result: {passed}/{total} passed")
        if passed == total:
            print("  All use cases passed!")
        else:
            print("  Some use cases did not match expected decisions.")
            print("  This may be due to LLM non-determinism in confidence scoring.")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
