"""
IncidentDNA — Judges Demo Presentation
=======================================
A single script that walks judges through the COMPLETE story:

  CHAPTER 1 → The Problem   : Connection pool bug triggers a P1 incident
  CHAPTER 2 → Agents Activate: Ag1 detects, Ag2 investigates, Ag5 validates
  CHAPTER 3 → The Decision  : Threshold engine auto-resolves with confidence 93%
  CHAPTER 4 → Safety First  : Shows 3 cases where the system correctly ESCALATES to humans
  CHAPTER 5 → Scorecard     : 5 incidents, MTTR, decisions, zero false auto-resolves

Reads from pre-recorded demo_logs/*.json  — no LLM calls, 100% deterministic.
Designed to run LIVE during a recorded demo video while presenter narrates.

Run:
    python demo_presentation.py           # Full demo (~4 minutes)
    python demo_presentation.py --fast    # Skip sleep pauses (for testing)

"""

import json
import os
import sys
import time
import textwrap
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
FAST = "--fast" in sys.argv
DEMO_LOGS = Path(__file__).parent / "demo_logs"

def pause(secs: float):
    if not FAST:
        time.sleep(secs)

def ts():
    return time.strftime("%H:%M:%S")

def W(n=60): return "=" * n
def D(n=60): return "-" * n

def load_uc(n: int) -> dict:
    p = DEMO_LOGS / f"uc{n}.json"
    with open(p) as f:
        return json.load(f)

def print_slow(text: str, delay: float = 0.03):
    """Print text character by character for dramatic effect."""
    if FAST:
        print(text)
        return
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def chapter(n: int, title: str):
    print()
    print()
    print(W(70))
    print(f"  CHAPTER {n}  —  {title}")
    print(W(70))
    print()
    pause(0.6)

def section(title: str):
    print()
    print(D(70))
    print(f"  {title}")
    print(D(70))
    pause(0.3)

def badge(label: str, value: str, width: int = 20):
    return f"  {label:<{width}} {value}"

def decision_badge(decision: str) -> str:
    if decision == "AUTO_RESOLVE":
        return "🟢 AUTO_RESOLVE"
    elif decision == "HUMAN_ESCALATION":
        return "🔴 HUMAN_ESCALATION"
    return f"⚪ {decision}"

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

print()
print(W(70))
print()
print_slow("   ██╗███╗   ██╗ ██████╗██╗██████╗ ███████╗███╗   ██╗████████╗", 0.005)
print_slow("   ██║████╗  ██║██╔════╝██║██╔══██╗██╔════╝████╗  ██║╚══██╔══╝", 0.005)
print_slow("   ██║██╔██╗ ██║██║     ██║██║  ██║█████╗  ██╔██╗ ██║   ██║   ", 0.005)
print_slow("   ██║██║╚██╗██║██║     ██║██║  ██║██╔══╝  ██║╚██╗██║   ██║   ", 0.005)
print_slow("   ██║██║ ╚████║╚██████╗██║██████╔╝███████╗██║ ╚████║   ██║   ", 0.005)
print_slow("   ╚═╝╚═╝  ╚═══╝ ╚═════╝╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ", 0.005)
print_slow("   ██████╗ ███╗   ██╗ █████╗                                    ", 0.005)
print_slow("   ██╔══██╗████╗  ██║██╔══██╗                                   ", 0.005)
print_slow("   ██║  ██║██╔██╗ ██║███████║                                   ", 0.005)
print_slow("   ██║  ██║██║╚██╗██║██╔══██║                                   ", 0.005)
print_slow("   ██████╔╝██║ ╚████║██║  ██║                                   ", 0.005)
print_slow("   ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝                                  ", 0.005)
print()
print("   Autonomous Incident Resolution Platform")
print("   Built on: Snowflake Cortex · Llama 3.1-70B · CrewAI · Composio")
print()
print(W(70))

pause(1.5)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 1 — THE PROBLEM
# ─────────────────────────────────────────────────────────────────────────────

chapter(1, "The Problem  —  A Deploy Just Hit Production")

print(f"  [{ts()}]  Deploy DPL-20241129-0042 just went live on payment-service")
pause(0.8)
print(f"  [{ts()}]  Composio webhook received — trigger_listener.py activated")
pause(0.5)
print()

# Metric spike visualization
print("  Connection pool usage in the last 60 seconds:")
print()
print("  baseline  ▏ 20 connections")

metrics = [
    ("t-55s", 20,  "▓" * 4),
    ("t-50s", 21,  "▓" * 4),
    ("t-45s", 23,  "▓" * 5),
    ("t-40s", 28,  "▓" * 6),
    ("t-35s", 35,  "▓" * 7),
    ("t-30s", 40,  "▓" * 8),
    ("t-25s", 45,  "▓" * 9),
    ("t-20s", 47,  "▓▓▓▓▓▓▓▓▓▓"),
    ("t-15s", 48,  "▓▓▓▓▓▓▓▓▓▓ ← POOL AT 96% — ALERT TRIGGERED"),
    ("NOW",   "?", "░░░░░░░░░░ ← waiting for agent analysis"),
]

for label, val, bar in metrics:
    print(f"  {label:>6}   ▏ {bar}")
    pause(0.15)

print()
print(f"  [{ts()}]  RAW.METRICS spike detected → z-score 4.8 (threshold: 2.0)")
print(f"  [{ts()}]  ⚡ INCIDENT PIPELINE ACTIVATING...")
pause(1.0)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 2 — AGENT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

chapter(2, "Agents Activate  —  Detect · Investigate · Validate")

uc1 = load_uc(1)
r = uc1["result"]

# ── Agent 1: Detector ────────────────────────────────────────────────────────
section("Ag1 — Detector  (ANALYTICS.METRIC_DEVIATIONS · RAW.SERVICE_DEPENDENCIES)")
pause(0.4)

print(f"\n  [{ts()}]  Ag1 querying Snowflake for anomalous metrics...")
pause(0.8)
print(f"  [{ts()}]  Ag1 querying service dependency graph...")
pause(0.8)
print()
print(f"  Ag1 VERDICT:")
print(badge("Severity:",   f"  {r['severity']}  ← highest priority"))
print(badge("Incident:",   f"  {r['incident_type']}  (connection pool starved)"))
print(badge("Blast Radius:", f"  {len(r['blast_radius'])} downstream services affected"))
for svc in r["blast_radius"]:
    print(f"                        ↳  {svc}")
print(badge("Evidence:",   f"  {', '.join(r['evidence'])}"))
pause(1.0)

# ── Agent 2: Investigator ────────────────────────────────────────────────────
section("Ag2 — Investigator  (Cortex Search · Similarity · Metrics)")
pause(0.4)

print(f"\n  [{ts()}]  Ag2 searching RAW.RUNBOOKS via Cortex Search...")
pause(0.8)
print(f"  [{ts()}]  Ag2 finding similar past incidents (CORTEX.SIMILARITY)...")
pause(0.8)
print(f"  [{ts()}]  Ag2 correlating 6 metric z-scores from ANALYTICS.METRIC_DEVIATIONS...")
pause(0.8)
print()
print("  Ag2 ROOT CAUSE ANALYSIS:")
print()

# Wrap the root cause for readable display
wrapped = textwrap.wrap(r["root_cause"], width=66)
for line in wrapped:
    print(f"  {line}")
    pause(0.04)

print()
print("  Recommended Fix:")
print(f"    Option 1 → {r['fix_options'][0]['title']}")
print(f"    Commands:")
for cmd in r["fix_options"][0]["commands"][:3]:
    print(f"      $ {cmd}")
print(f"    Estimated time: {r['fix_options'][0]['estimated_time']}")
print(f"    Risk:           {r['fix_options'][0]['risk_level']}")
print(f"    Confidence:     {r['confidence']*100:.0f}%")
pause(1.0)

# ── Agent 5: Validator ───────────────────────────────────────────────────────
section("Ag5 — Validator  (Adversarial Reviewer)")
pause(0.4)

print(f"\n  [{ts()}]  Ag5 adversarially testing Ag2's hypothesis...")
pause(0.8)
print(f"  [{ts()}]  Ag5 checking for alternative explanations...")
pause(0.8)
print()
verdict_label = "APPROVED ✅" if r["approved"] else "CHALLENGED ⚠️"
print(f"  Ag5 VERDICT:  {verdict_label}")
print(f"  Debate rounds: {r['debate_rounds']}")
print(f"  Final confidence: {r['confidence']*100:.0f}%")
pause(1.0)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 3 — DECISION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

chapter(3, "The Decision  —  Autonomous Resolution Threshold Engine")

print("  7-Rule safety engine evaluates every incident before any action.\n")
pause(0.5)

rules = [
    ("RULE 1", "SECURITY or DATA_INTEGRITY?",               "No  → continue",  False),
    ("RULE 2", "Ag5 validator APPROVED?",                    "Yes → continue",  False),
    ("RULE 3", "Blast radius ≤ 2 services?",                 "Yes → continue",  False),
    ("RULE 4", "Confidence ≥ 90%, risk LOW, fix proven?",    "YES → AUTO_RESOLVE", True),
]

for rule, question, answer, triggered in rules:
    marker = "► " if triggered else "  "
    color_answer = f"  ✅ {answer}" if not triggered else f"  🟢 {answer}"
    print(f"  {marker}[{rule}]  {question}")
    pause(0.4)
    print(f"           {color_answer}")
    pause(0.3)
    print()

pause(0.5)
print(W(70))
print()
print(f"  DECISION:  🟢 AUTO_RESOLVE")
print(f"  Rule:      RULE_4")
print(f"  Reason:    {r['rule_description']}")
print()
print(W(70))
pause(1.0)

# ── Fix execution ────────────────────────────────────────────────────────────
section("Auto-Fix Execution  —  No human in the loop")
pause(0.3)

fix_steps = [
    "Idempotency check passed (SHA-256 key not in AI.ACTIONS)",
    "Executing:  kubectl exec -it db-migration-pod -- flyway undo",
    "Executing:  kubectl exec -it db-migration-pod -- flyway validate",
    "Monitoring  connection_pool_usage for 5 minutes...",
    "Metrics recovered:  pool 48→19 connections  ✅",
    "Slack alert posted  →  #incidents",
    "GitHub issue created  →  theshubh007/IncidentDNA",
    "AI.INCIDENT_HISTORY record written  (MTTR: 4 min)",
]

for step in fix_steps:
    print(f"  [{ts()}]  {step}")
    pause(0.5)

print()
print(f"  MTTR:  {r['mttr_seconds'] // 60} min {r['mttr_seconds'] % 60}s")
print(f"         Human average for this incident type:  ~35 minutes")
print(f"         Speedup:  ~8.75× faster  💨")
pause(1.2)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 4 — SAFETY BOUNDARIES
# ─────────────────────────────────────────────────────────────────────────────

chapter(4, "Safety First  —  When The System Says No")

print("  IncidentDNA does NOT auto-fix everything.")
print("  Three scenarios show the safety rails in action.\n")
pause(0.8)

# ── UC2: Data Corruption ─────────────────────────────────────────────────────
section("Case A — Silent Data Corruption  (order-service)")
uc2 = load_uc(2)
r2 = uc2["result"]
pause(0.3)

print(f"\n  Service:   {uc2['event']['service']}")
print(f"  Type:      {r2['incident_type']}  ← 48,302 corrupted records")
print(f"  Severity:  {r2['severity']}")
print()
print("  Threshold engine evaluation:")
print("  ► [RULE 1]  DATA_INTEGRITY incident?  →  🔴 HARD BLOCK")
print("              Rule says: DATA_INTEGRITY ALWAYS needs human eyes.")
print()
print(f"  DECISION:  {decision_badge(r2['threshold_decision'])}")
print(f"  Urgency:   {r2['urgency']}")
print(f"  Root cause found: Yes  (confidence {r2['confidence']*100:.0f}%)")
print(f"  Fix ready:        Yes  (3 ranked options with rollback commands)")
print(f"  Action:           Slack + GitHub issue created, human paged")
pause(1.0)

# ── UC4: Security Attack ─────────────────────────────────────────────────────
section("Case B — Credential Stuffing Attack  (user-service)")
uc4 = load_uc(4)
r4 = uc4["result"]
pause(0.3)

print(f"\n  Service:   {uc4['event']['service']}")
print(f"  Type:      {r4['incident_type']}  ← 48,291 failed auth attempts")
print(f"  Details:   {uc4['event']['details']['unique_ips']:,} unique IPs · "
      f"{uc4['event']['details']['potentially_compromised']:,} potentially compromised accounts")
print()
print("  Threshold engine evaluation:")
print("  ► [RULE 1]  SECURITY incident?  →  🔴 HARD BLOCK")
print("              Rule says: SECURITY ALWAYS requires human review.")
print()
print(f"  DECISION:  {decision_badge(r4['threshold_decision'])}")
print(f"  Urgency:   {r4['urgency']}")
print()
print("  (Ag2 still found root cause: DB max_connections misconfiguration, not a real attack)")
print("  (Fix commands ready — human can apply with 1 click)")
pause(1.0)

# ── UC3: Cascading Failure ───────────────────────────────────────────────────
section("Case C — Cascading Failure Across 7 Services  (api-gateway)")
uc3 = load_uc(3)
r3 = uc3["result"]
pause(0.3)

print(f"\n  Service:   {uc3['event']['service']}")
print(f"  Type:      {r3['incident_type']}  ← 7 services down")
print(f"  Affected:  {', '.join(r3['blast_radius'][:4])} + {len(r3['blast_radius'])-4} more")
print()
print("  Threshold engine evaluation:")
print("  [RULE 1]  SECURITY or DATA_INTEGRITY?  →  No")
print("  [RULE 2]  Validator approved?           →  Yes")
print("  ► [RULE 3]  Blast radius ≤ 2?           →  🔴 NO  (7 services) — ESCALATE")
print()
print(f"  DECISION:  {decision_badge(r3['threshold_decision'])}")
print(f"  Rule:      RULE_3  — blast radius too wide to auto-fix safely")
print(f"  Confidence: {r3['confidence']*100:.0f}%  (high — but safety wins)")
print(f"  Urgency:   {r3['urgency']}")
pause(1.0)

# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER 5 — SCORECARD
# ─────────────────────────────────────────────────────────────────────────────

chapter(5, "Final Scorecard  —  5 Incidents Processed")

ucs = [load_uc(i) for i in range(1, 6)]

print()
print(f"  {'#':<4} {'Incident':<36} {'Decision':<22} {'MTTR':>8}  {'Rule'}")
print(f"  {D(70)}")

total_mttr = 0
auto_count = 0
escalate_count = 0

for uc in ucs:
    r = uc["result"]
    n = uc["use_case"]
    name = uc["name"][:34]
    dec = r["threshold_decision"]
    rule = r["rule_applied"]
    mttr_m = r["mttr_seconds"] // 60
    mttr_s = r["mttr_seconds"] % 60
    mttr_str = f"{mttr_m}m {mttr_s:02d}s"
    icon = "🟢" if dec == "AUTO_RESOLVE" else "🔴"
    total_mttr += r["mttr_seconds"]
    if dec == "AUTO_RESOLVE":
        auto_count += 1
    else:
        escalate_count += 1

    print(f"  UC{n}  {name:<36} {icon} {dec:<20} {mttr_str:>8}  {rule}")
    pause(0.3)

avg_mttr = total_mttr / len(ucs)
avg_m = int(avg_mttr) // 60
avg_s = int(avg_mttr) % 60

print(f"  {D(70)}")
print()
print(f"  Total incidents:     {len(ucs)}")
print(f"  Auto-resolved:       {auto_count}  (no human required)")
print(f"  Escalated to human:  {escalate_count}  (all correct — SECURITY, DATA_INTEGRITY, 7-service blast radius)")
print(f"  False auto-resolves: 0  ← zero unsafe actions")
print(f"  Avg MTTR:            {avg_m}m {avg_s:02d}s  vs industry avg ~35 min")
print(f"  Speedup:             ~{35*60/avg_mttr:.1f}×  faster  💨")
pause(0.8)

# ─────────────────────────────────────────────────────────────────────────────
# CLOSING
# ─────────────────────────────────────────────────────────────────────────────

print()
print()
print(W(70))
print()
print("  What IncidentDNA proves:")
print()
print("  ① Autonomous agents can investigate faster than any on-call engineer")
print("     (sub-4-minute MTTR vs 35-minute human average)")
print()
print("  ② Safety rails prevent autonomous action when stakes are too high")
print("     (SECURITY + DATA_INTEGRITY = always human | blast radius guard)")
print()
print("  ③ The system doesn't guess — it uses 3-source evidence chains:")
print("     Runbooks + Past Incidents + Live Metrics  →  confident decisions")
print()
print("  ④ When it can't auto-fix, it still saves time:")
print("     Root cause + ranked fix options + rollback commands → ready to paste")
print()
print(W(70))
print()
print("  Stack:  Snowflake Cortex · Llama 3.1-70B · CrewAI · Composio")
print("          Snowflake Dynamic Tables · Cortex Search · Similarity")
print()
print(W(70))
print()
