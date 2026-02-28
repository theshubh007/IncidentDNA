"""
DEMO 4: Pool Exhaustion — System Failure Under Load
====================================================
The critical failure scenario:
  - Pool has 3 connections (max_connections=3)
  - 3 threads acquire all connections and enter a retry sleep (holding them)
  - A 4th thread tries to acquire → pool exhausted → TimeoutError after 2s
  - Shows the exact moment the system fails

Timeline:
  t=0s  Thread-1/2/3 each acquire a connection, fail, sleep 3s
  t=0s  Thread-4 tries to acquire — BLOCKED (in_use=3, available=0)
  t=2s  Thread-4 TIMES OUT — pool still exhausted

Run: python demo_04_pool_exhaustion.py
"""

import sys
import os
import time
import threading
import logging
logging.disable(logging.CRITICAL)  # Suppress internal pool logs for clean demo output

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'broker'))
from db_pool import ConnectionPool

def ts():
    return time.strftime("%H:%M:%S")

def sep():
    print("-" * 60)

print()
print("=" * 60)
print("  DEMO 4: Pool Exhaustion — System Failure Under Load")
print("=" * 60)
print()

# ── Step 1: Initialize pool with 3 connections ─────────────
print(f"[{ts()}] Initializing pool (max=3, timeout=2s)...")
pool = ConnectionPool(max_connections=3, connection_timeout=2.0)
print(f"[{ts()}] Pool ready — 3 connections maximum.")
time.sleep(0.4)

sep()

# ── Shared state ────────────────────────────────────────────
acquired_count = [0]
all_acquired = threading.Event()   # Signals when all 3 slow threads have connections
results = {}
lock = threading.Lock()

# ── Workers 1-3: acquire + fail + sleep (holding connection) ─
def slow_worker(worker_id):
    try:
        conn = pool.acquire()
        with lock:
            print(f"[{ts()}] [Thread-{worker_id}] ✅ Acquired conn-{conn['id']}")
            acquired_count[0] += 1
            if acquired_count[0] == 3:
                all_acquired.set()  # Signal: all 3 connections grabbed

        all_acquired.wait()  # Wait until all 3 threads have their connections

        with lock:
            s = pool.get_stats()
            if worker_id == 1:  # Only print once
                print(f"\n[{ts()}] All 3 threads holding connections → in_use={s['in_use']}  available={s['available']}")
                print(f"[{ts()}] All 3 threads now SLEEPING 3s before retry (holding connections!)...\n")

        time.sleep(3.0)  # Simulate retry delay — holding the connection the whole time

        pool.release(conn)
        with lock:
            results[worker_id] = "released"
            print(f"[{ts()}] [Thread-{worker_id}] Released conn-{conn['id']} after 3s sleep")

    except Exception as e:
        with lock:
            results[worker_id] = f"ERROR: {e}"
            print(f"[{ts()}] [Thread-{worker_id}] ❌ ERROR: {e}")

# ── Worker 4: tries to acquire after pool is full ───────────
worker4_start = [None]

def timeout_worker():
    # Wait for all 3 slow workers to have grabbed connections
    all_acquired.wait()
    time.sleep(0.2)  # Small gap so output is clean

    worker4_start[0] = time.time()
    with lock:
        s = pool.get_stats()
        print(f"[{ts()}] [Thread-4] Attempting to acquire... pool → in_use={s['in_use']}  available={s['available']}")

    try:
        conn = pool.acquire()  # Will timeout after 2s
        pool.release(conn)
        with lock:
            results[4] = "acquired (unexpected)"
    except TimeoutError as e:
        elapsed = time.time() - worker4_start[0]
        with lock:
            results[4] = f"TIMEOUT after {elapsed:.2f}s"
            print(f"[{ts()}] [Thread-4] ❌ TimeoutError after {elapsed:.2f}s — {e}")

# ── Step 2: Launch all 4 threads ────────────────────────────
print(f"\n[{ts()}] Launching Thread-1, Thread-2, Thread-3 (slow, retry-holding)...")
print(f"[{ts()}] Launching Thread-4 (fast query — will try to acquire)...\n")
time.sleep(0.3)

sep()

threads = []
for i in range(1, 4):
    t = threading.Thread(target=slow_worker, args=(i,), name=f"Thread-{i}")
    threads.append(t)

t4 = threading.Thread(target=timeout_worker, name="Thread-4")
threads.append(t4)

for t in threads:
    t.start()

for t in threads:
    t.join()

# ── Step 3: Final scorecard ─────────────────────────────────
sep()
print()
s = pool.get_stats()
print(f"[{ts()}] Final pool stats → in_use={s['in_use']}  available={s['available']}")
print()
print("FINAL SCORECARD:")
for wid in sorted(results):
    icon = "✅" if "released" in results[wid] else "❌"
    label = f"Thread-{wid} (logging)" if wid <= 3 else f"Thread-{wid} (query)  "
    print(f"  {icon} {label}: {results[wid]}")

print()
sep()
print()
print("ROOT CAUSE: Threads 1-3 held connections while sleeping 3s between retries.")
print("            Thread-4 could not acquire a connection for its 2s timeout window.")
print("            The pool was 100% occupied by sleeping retry logic — not real work.")
print()
print("RESULT: Pool fully exhausted. Thread-4 (fast query) timed out.")
print("        3 sleeping retries blocked the entire connection pool for 3 seconds.")
print("=" * 60)
print()
