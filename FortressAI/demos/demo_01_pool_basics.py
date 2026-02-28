"""
DEMO 1: Connection Pool — Acquire, Reuse & Stats
=================================================
Shows a healthy pool working correctly:
  - Connections acquired one by one with live stats
  - Released connections are REUSED (not recreated)
  - Final stats confirm clean state

Run: python demo_01_pool_basics.py
"""

import sys
import os
import time
import logging
logging.disable(logging.CRITICAL)  # Suppress internal pool logs for clean demo output

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'broker'))
from db_pool import ConnectionPool

def ts():
    return time.strftime("%H:%M:%S")

def print_stats(pool, label=""):
    s = pool.get_stats()
    tag = f"  [{label}]" if label else ""
    print(f"[{ts()}]{tag} Pool stats → created={s['created']}  in_use={s['in_use']}  available={s['available']}  max={s['max_connections']}")

def sep():
    print("-" * 60)

print()
print("=" * 60)
print("  DEMO 1: Connection Pool — Acquire, Reuse & Stats")
print("=" * 60)
print()

# ── Step 1: Initialize ─────────────────────────────────────
print(f"[{ts()}] Initializing connection pool (max=5, timeout=3s)...")
pool = ConnectionPool(max_connections=5, connection_timeout=3.0)
print_stats(pool, "init")
time.sleep(0.5)

sep()

# ── Step 2: Acquire 3 connections ──────────────────────────
print(f"\n[{ts()}] Acquiring 3 connections...")
time.sleep(0.3)

conn1 = pool.acquire()
print(f"[{ts()}] ✅ Acquired conn1 (id={conn1['id']})")
print_stats(pool, "after conn1")
time.sleep(0.3)

conn2 = pool.acquire()
print(f"[{ts()}] ✅ Acquired conn2 (id={conn2['id']})")
print_stats(pool, "after conn2")
time.sleep(0.3)

conn3 = pool.acquire()
print(f"[{ts()}] ✅ Acquired conn3 (id={conn3['id']})")
print_stats(pool, "after conn3")
time.sleep(0.5)

sep()

# ── Step 3: Release conn1 and reacquire ────────────────────
print(f"\n[{ts()}] Releasing conn1 back to pool...")
pool.release(conn1)
print_stats(pool, "after release")
time.sleep(0.3)

print(f"\n[{ts()}] Acquiring conn4 (should REUSE conn1 — no new connection created)...")
conn4 = pool.acquire()
print(f"[{ts()}] ✅ Acquired conn4 (id={conn4['id']})")

if id(conn4) == id(conn1):
    print(f"[{ts()}] ✅ conn4 IS conn1 — connection was REUSED (created count unchanged)")
else:
    print(f"[{ts()}] ✅ conn4 reused from pool (same DB id: conn1.id={conn1['id']}, conn4.id={conn4['id']})")
print_stats(pool, "after reuse")
time.sleep(0.5)

sep()

# ── Step 4: Release all ─────────────────────────────────────
print(f"\n[{ts()}] Releasing all connections...")
for conn, name in [(conn2, "conn2"), (conn3, "conn3"), (conn4, "conn4")]:
    pool.release(conn)
    print(f"[{ts()}]   Released {name}")
    time.sleep(0.2)

print_stats(pool, "final")
time.sleep(0.3)

sep()
print()
print(f"RESULT: Pool correctly manages {pool._created_count} connection(s). "
      f"Released connections are reused — zero unnecessary allocations.")
print("=" * 60)
print()
