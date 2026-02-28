# tools/demo_utils.py
"""
DEMO_MODE utilities for IncidentDNA.
Only active when DEMO_MODE=true in environment.
All functions are no-ops if DEMO_MODE is not set.
"""

import os
import time
from datetime import datetime, timezone

from utils.snowflake_conn import run_dml

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"


def inject_anomalous_metrics(service_name: str, spike_multiplier: float = 10.0):
    """
    Inject simulated anomalous metrics into RAW.METRICS for demo purposes.
    ONLY runs when DEMO_MODE=true. Safe no-op otherwise.
    Uses run_dml (same pattern as ingestion/trigger_listener.py).
    """
    if not DEMO_MODE:
        return

    try:
        print(f"[DEMO_MODE] Injecting anomalous metrics for {service_name}...")

        # RAW.METRICS schema: metric_id (auto UUID), service_name, metric_name, metric_value, recorded_at (auto)
        run_dml(
            """INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
               VALUES (%s, %s, %s)""",
            (service_name, "error_rate", 0.22),
        )
        run_dml(
            """INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
               VALUES (%s, %s, %s)""",
            (service_name, "latency_p99", 2100.0),
        )
        run_dml(
            """INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
               VALUES (%s, %s, %s)""",
            (service_name, "cpu_pct", 78.0),
        )

        print(f"[DEMO_MODE] ✅ Anomalous metrics injected for {service_name}")

    except Exception as e:
        print(f"[DEMO_MODE] ⚠️ Failed to inject metrics (non-fatal): {e}")


def inject_recovery_metrics(service_name: str, delay_seconds: float = 5.0):
    """
    After a fix is applied, inject normalized metrics to simulate recovery.
    ONLY runs when DEMO_MODE=true.
    """
    if not DEMO_MODE:
        return

    try:
        time.sleep(delay_seconds)
        print(f"[DEMO_MODE] Injecting recovery metrics for {service_name}...")

        run_dml(
            """INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
               VALUES (%s, %s, %s)""",
            (service_name, "error_rate", 0.02),
        )
        run_dml(
            """INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
               VALUES (%s, %s, %s)""",
            (service_name, "latency_p99", 210.0),
        )
        run_dml(
            """INSERT INTO RAW.METRICS (service_name, metric_name, metric_value)
               VALUES (%s, %s, %s)""",
            (service_name, "cpu_pct", 45.0),
        )

        print(f"[DEMO_MODE] ✅ Recovery metrics injected for {service_name}")

    except Exception as e:
        print(f"[DEMO_MODE] ⚠️ Failed to inject recovery metrics (non-fatal): {e}")


def simulate_fix_execution(fix_command: str, service_name: str) -> bool:
    """
    Simulate executing a fix command in DEMO_MODE.
    Returns True on success, False on failure.
    Always simulates in DEMO_MODE (no real subprocess execution).
    When DEMO_MODE is off, this is a no-op returning True (real fix logic lives elsewhere).
    """
    if DEMO_MODE:
        try:
            print(f"[DEMO_MODE] Simulating fix execution:")
            print(f"[DEMO_MODE]   $ {fix_command}")
            time.sleep(1)
            print(f"[DEMO_MODE] ✅ Fix simulated successfully for {service_name}")
            return True
        except Exception as e:
            print(f"[DEMO_MODE] ⚠️ Fix simulation error (non-fatal): {e}")
            return False
    else:
        # Non-demo: no-op — real fix execution is not implemented (no k8s cluster)
        return True
