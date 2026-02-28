"""
DEMO 2: Retry Logic — Transient Failure Recovery
=================================================
Shows @with_db_retry handling a flaky database write:
  - Attempt 1: fails immediately (ConnectionError)
  - Attempt 2: fails again (ConnectionError)
  - Attempt 3: succeeds
  - Exponential backoff timing is visible in the output

Run: python demo_02_retry_success.py
"""

import sys
import os
import time
import logging
logging.disable(logging.CRITICAL)  # Suppress internal pool logs for clean demo output

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'broker'))
from db_pool import ConnectionPool, initialize_pool, get_pool, with_db_retry

def ts():
    return time.strftime("%H:%M:%S")

def sep():
    print("-" * 60)

print()
print("=" * 60)
print("  DEMO 2: Retry Logic — Transient Failure Recovery")
print("=" * 60)
print()

# ── Step 1: Initialize ─────────────────────────────────────
print(f"[{ts()}] Initializing pool (max=5)...")
initialize_pool(max_connections=5, connection_timeout=10.0)
pool = get_pool()
print(f"[{ts()}] Pool ready.")
time.sleep(0.4)

sep()

# ── Step 2: Define a flaky operation ───────────────────────
print(f"\n[{ts()}] Defining save_audit_log() with @with_db_retry(max_attempts=3, delay=0.3, backoff=2.0)")
print(f"[{ts()}] Simulating a DB write that fails twice then succeeds on the 3rd attempt.\n")
time.sleep(0.5)

attempt_count = 0
attempt_times = []

@with_db_retry(max_attempts=3, delay=0.3, backoff=2.0)
def save_audit_log(conn):
    global attempt_count
    attempt_count += 1
    attempt_times.append(time.time())

    print(f"[{ts()}] → Attempt {attempt_count}/3 ... ", end="", flush=True)

    if attempt_count < 3:
        print(f"❌ FAILED  (ConnectionError: DB write unavailable)")
        raise ConnectionError("DB write unavailable")

    print(f"✅ SUCCESS  (audit log saved, conn_id={conn['id']})")
    return {"status": "saved", "conn_id": conn["id"], "attempts": attempt_count}

# ── Step 3: Call it and observe output ─────────────────────
sep()
print(f"[{ts()}] Calling save_audit_log()...\n")

start = time.time()
result = save_audit_log()
elapsed = time.time() - start

sep()

# ── Step 4: Show timing ────────────────────────────────────
print()
if len(attempt_times) >= 2:
    d1 = attempt_times[1] - attempt_times[0]
    print(f"[{ts()}] Delay between attempt 1→2: {d1:.2f}s  (base delay = 0.3s)")
if len(attempt_times) >= 3:
    d2 = attempt_times[2] - attempt_times[1]
    print(f"[{ts()}] Delay between attempt 2→3: {d2:.2f}s  (backoff ×2 = 0.6s)")

print(f"[{ts()}] Total elapsed: {elapsed:.2f}s")
print()

s = pool.get_stats()
print(f"[{ts()}] Pool stats → created={s['created']}  in_use={s['in_use']}  available={s['available']}")
print()

sep()
print()
print(f"RESULT: save_audit_log() succeeded on attempt {result['attempts']}/3.")
print(f"        Exponential backoff: 0.3s → 0.6s. Connection released cleanly.")
print("=" * 60)
print()
