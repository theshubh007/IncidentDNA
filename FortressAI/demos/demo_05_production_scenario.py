"""
DEMO 5: Production Simulation — 5 Concurrent Requests
======================================================
Realistic production load showing cascading failure:
  - Pool: 3 connections, timeout=4s
  - Workers 1, 2, 3: "logging" operations — always fail, retry with 2s delay
    (grab all 3 connections, enter retry sleep while holding them)
  - Workers 4, 5: "fast queries" — would succeed instantly IF they get a connection
    (but can't get one → wait 4s → TimeoutError)

This is the real-world failure mode: slow retrying operations block fast ones.

Run: python demo_05_production_scenario.py
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
print("  DEMO 5: Production Simulation — 5 Concurrent Requests")
print("=" * 60)
print()

# ── Step 1: Initialize pool ─────────────────────────────────
print(f"[{ts()}] Initializing pool (max=3, timeout=3.5s)...")
pool = ConnectionPool(max_connections=3, connection_timeout=3.5)
print(f"[{ts()}] Pool ready — simulating production: 5 concurrent workers, 3 connections, 3.5s timeout.")
time.sleep(0.4)

sep()

# ── Shared state ────────────────────────────────────────────
results = {}
lock = threading.Lock()
start_time = [None]

# Barrier so all 5 workers start at the same moment
ready_barrier = threading.Barrier(5)

# ── Logging worker (1-3): fails, holds connection during 2s retry sleep ─────
def logging_worker(worker_id):
    ready_barrier.wait()

    t_start = time.time()
    attempt = 0
    max_attempts = 3
    retry_delay = 2.0

    try:
        conn = pool.acquire()
        elapsed = time.time() - start_time[0]

        with lock:
            s = pool.get_stats()
            print(f"[{ts()}] [Worker-{worker_id}] +{elapsed:.1f}s ✅ Got conn-{conn['id']}  "
                  f"(pool → in_use={s['in_use']}  available={s['available']})")

        try:
            while attempt < max_attempts:
                attempt += 1
                # Always fail — simulate persistently broken DB write
                with lock:
                    elapsed = time.time() - start_time[0]
                    print(f"[{ts()}] [Worker-{worker_id}] +{elapsed:.1f}s Attempt {attempt}/{max_attempts} → "
                          f"❌ FAILED — sleeping {retry_delay}s (holding conn-{conn['id']}!)")

                if attempt < max_attempts:
                    time.sleep(retry_delay)  # BUG: holding connection during sleep!
                else:
                    total = time.time() - t_start
                    with lock:
                        results[worker_id] = {
                            "type": "logging",
                            "status": "FAILED",
                            "detail": f"failed after {max_attempts} attempts ({total:.1f}s total)"
                        }
        finally:
            pool.release(conn)

    except TimeoutError as e:
        elapsed = time.time() - t_start
        with lock:
            results[worker_id] = {
                "type": "logging",
                "status": "TIMEOUT",
                "detail": f"timed out after {elapsed:.1f}s waiting for connection"
            }
            print(f"[{ts()}] [Worker-{worker_id}] ❌ TIMEOUT after {elapsed:.1f}s — {e}")

# ── Query worker (4-5): fast, succeeds if it can get a connection ─────────
def query_worker(worker_id):
    ready_barrier.wait()

    t_start = time.time()

    # Small stagger so logging workers grab connections first
    time.sleep(0.05)

    try:
        with lock:
            s = pool.get_stats()
            elapsed = time.time() - start_time[0]
            print(f"[{ts()}] [Worker-{worker_id}] +{elapsed:.1f}s Trying to acquire... "
                  f"(pool → in_use={s['in_use']}  available={s['available']})")

        conn = pool.acquire()  # Blocks until timeout

        elapsed = time.time() - t_start
        with lock:
            print(f"[{ts()}] [Worker-{worker_id}] ✅ Got conn-{conn['id']} after {elapsed:.1f}s")

        # Fast query — would complete immediately
        time.sleep(0.05)
        pool.release(conn)

        total = time.time() - t_start
        with lock:
            results[worker_id] = {
                "type": "fast-query",
                "status": "SUCCESS",
                "detail": f"completed in {total:.2f}s"
            }

    except TimeoutError as e:
        elapsed = time.time() - t_start
        with lock:
            results[worker_id] = {
                "type": "fast-query",
                "status": "TIMEOUT",
                "detail": f"timed out after {elapsed:.1f}s — never got a connection"
            }
            print(f"[{ts()}] [Worker-{worker_id}] ❌ TIMEOUT after {elapsed:.1f}s — {e}")

# ── Step 2: Launch all 5 workers ────────────────────────────
print(f"\n[{ts()}] Launching 5 concurrent workers:")
print(f"[{ts()}]   Workers 1-3: DB logging (failing, retry with 2s sleep — will hold connections)")
print(f"[{ts()}]   Workers 4-5: Fast queries (should be instant — but can they get a connection?)")
print()
time.sleep(0.5)

sep()

threads = []

start_time[0] = time.time()

for i in range(1, 4):
    t = threading.Thread(target=logging_worker, args=(i,), name=f"Worker-{i}")
    threads.append(t)

for i in range(4, 6):
    t = threading.Thread(target=query_worker, args=(i,), name=f"Worker-{i}")
    threads.append(t)

for t in threads:
    t.start()

for t in threads:
    t.join()

# ── Step 3: Final scorecard ─────────────────────────────────
sep()
print()
s = pool.get_stats()
total_elapsed = time.time() - start_time[0]
print(f"[{ts()}] Simulation complete in {total_elapsed:.1f}s")
print(f"[{ts()}] Final pool stats → in_use={s['in_use']}  available={s['available']}")
print()

print("FINAL SCORECARD:")
print()
for wid in sorted(results):
    r = results[wid]
    icon = "✅" if r["status"] == "SUCCESS" else "❌"
    worker_type = f"Worker-{wid} ({r['type']})"
    print(f"  {icon} {worker_type:<26}: {r['status']} — {r['detail']}")

print()
sep()
print()
print("ROOT CAUSE: Workers 1-3 acquired all 3 connections, then entered 2s retry")
print("            sleeps. During those sleeps, connections were unavailable.")
print("            Workers 4-5 (fast queries that WOULD have succeeded) timed out")
print("            waiting 4s — never got a connection despite doing no real work.")
print()
print("IMPACT:     Retry logic in logging paths starved healthy query operations.")
print("            Pool exhaustion cascaded into total system unavailability.")
print()
print("FIX:        Release connection BEFORE sleeping. Reacquire on each attempt.")
print("            This lets other callers use the pool during retry delays.")
print("=" * 60)
print()
