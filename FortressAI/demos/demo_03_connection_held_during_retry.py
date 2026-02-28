"""
DEMO 3: The Bug — Connection Held During Retry Sleep
=====================================================
X-ray view of the core bug in with_db_retry:
  - Thread A acquires the only connection, fails, sleeps 2s before retry
  - While Thread A sleeps: pool shows in_use=1, available=0
  - Thread B tries to acquire during Thread A's sleep → BLOCKS waiting
  - Thread A eventually succeeds → releases → Thread B finally gets in
  - Shows exactly how long Thread B had to wait because of Thread A's sleep

Pool size: 1 connection (makes the block obvious)

Run: python demo_03_connection_held_during_retry.py
"""

import sys
import os
import time
import threading
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
print("  DEMO 3: The Bug — Connection Held During Retry Sleep")
print("=" * 60)
print()

# ── Step 1: Initialize pool with only 1 connection ─────────
print(f"[{ts()}] Initializing pool (max=1, timeout=10s)...")
initialize_pool(max_connections=1, connection_timeout=10.0)
pool = get_pool()
print(f"[{ts()}] Pool ready — only 1 connection available.")
time.sleep(0.4)

sep()

# ── Shared state ────────────────────────────────────────────
thread_a_sleeping = threading.Event()
thread_b_done = threading.Event()
thread_b_wait_start = [None]
thread_b_wait_end = [None]
thread_b_result = [None]
thread_a_result = [None]

# ── Thread A: acquires connection, fails, sleeps 2s ─────────
attempt_a = [0]

@with_db_retry(max_attempts=2, delay=2.0, backoff=1.0)
def thread_a_operation(conn):
    attempt_a[0] += 1
    if attempt_a[0] == 1:
        print(f"[{ts()}] [Thread-A] Attempt 1 → ❌ FAILED — now sleeping 2s before retry...")
        print(f"[{ts()}] [Thread-A] Connection conn-{conn['id']} is IN-USE during sleep!")
        thread_a_sleeping.set()  # Signal that Thread A is now sleeping
        # with_db_retry will sleep 2.0s here while holding the connection
        raise ConnectionError("Simulated transient DB error")
    else:
        print(f"[{ts()}] [Thread-A] Attempt 2 → ✅ SUCCESS — releasing connection now.")
        return "Thread-A done"

def run_thread_a():
    try:
        result = thread_a_operation()
        thread_a_result[0] = result
    except Exception as e:
        thread_a_result[0] = f"FAILED: {e}"

# ── Thread B: tries to acquire while Thread A is sleeping ───
def run_thread_b():
    # Wait until Thread A has its connection and is sleeping
    thread_a_sleeping.wait()
    time.sleep(0.1)  # Small offset so output is clearly after Thread A's message

    print(f"\n[{ts()}] [Thread-B] Trying to acquire a connection...")
    s = pool.get_stats()
    print(f"[{ts()}] [Thread-B] Pool stats → in_use={s['in_use']}  available={s['available']}  (BLOCKED!)")

    thread_b_wait_start[0] = time.time()
    try:
        conn = pool.acquire()  # This will block until Thread A releases
        thread_b_wait_end[0] = time.time()
        wait_time = thread_b_wait_end[0] - thread_b_wait_start[0]
        print(f"[{ts()}] [Thread-B] ✅ Finally got connection conn-{conn['id']} after waiting {wait_time:.2f}s")
        pool.release(conn)
        thread_b_result[0] = wait_time
    except Exception as e:
        thread_b_wait_end[0] = time.time()
        thread_b_result[0] = f"FAILED: {e}"
    finally:
        thread_b_done.set()

# ── Step 2: Launch both threads ─────────────────────────────
print(f"\n[{ts()}] Launching Thread-A and Thread-B simultaneously...")
print(f"[{ts()}] Thread-A: flaky DB write (will fail, sleep 2s, then retry)")
print(f"[{ts()}] Thread-B: simple acquire (will BLOCK while Thread-A sleeps)\n")
time.sleep(0.3)

sep()

t_a = threading.Thread(target=run_thread_a, name="Thread-A")
t_b = threading.Thread(target=run_thread_b, name="Thread-B")

t_a.start()
t_b.start()

# ── Step 3: Monitor pool stats while threads run ────────────
print(f"\n[{ts()}] [Monitor] Watching pool stats every 0.5s...")

monitor_start = time.time()
for i in range(8):
    time.sleep(0.5)
    if thread_b_done.is_set() and not t_a.is_alive():
        break
    s = pool.get_stats()
    elapsed = time.time() - monitor_start
    print(f"[{ts()}] [Monitor] +{elapsed:.1f}s → in_use={s['in_use']}  available={s['available']}")

t_a.join()
t_b.join()

sep()

# ── Step 4: Final report ────────────────────────────────────
print()
print(f"[{ts()}] Thread-A result: {thread_a_result[0]}")

if isinstance(thread_b_result[0], float):
    print(f"[{ts()}] Thread-B waited: {thread_b_result[0]:.2f}s  ← blocked by Thread-A's retry sleep")
else:
    print(f"[{ts()}] Thread-B result: {thread_b_result[0]}")

s = pool.get_stats()
print(f"[{ts()}] Final pool stats → in_use={s['in_use']}  available={s['available']}")
print()

sep()
print()
print("ROOT CAUSE: with_db_retry acquires the connection BEFORE the retry loop.")
print("            It then sleeps between attempts while HOLDING the connection.")
print("            Any other caller must WAIT — even for a completely different query.")
print()
print(f"RESULT: Thread-B was blocked for ~2s by Thread-A's retry sleep.")
print("        With max_connections=1, the whole system freezes during retries.")
print("=" * 60)
print()
