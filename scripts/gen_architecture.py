#!/usr/bin/env python3
"""
Auto-updates ARCHITECTURE.md with current codebase status.
Runs on: git commit, git pull/merge, Claude Code file edits.

What it updates:
  - STATUS_START/STATUS_END block (which files exist)
  - FILES_START/FILES_END block (directory tree with status badges)
"""

import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
ARCH_FILE = ROOT / "ARCHITECTURE.md"


# ── Key files to track ────────────────────────────────────────────────────────

COMPONENTS = [
    {
        "name": "Agent Layer",
        "files": [
            "agents/manager.py",
            "agents/ag1_detector.py",
            "agents/ag2_investigator.py",
            "agents/ag5_validator.py",
            "agents/crew.py",
        ],
        "partial_ok": False,
    },
    {
        "name": "Tools",
        "files": [
            "tools/query_snowflake.py",
            "tools/search_runbooks.py",
            "tools/find_similar_incidents.py",
            "tools/composio_actions.py",
            "tools/idempotency.py",
        ],
        "partial_ok": False,
    },
    {
        "name": "Utils",
        "files": [
            "utils/snowflake_conn.py",
            "utils/snowflake_llm.py",
        ],
        "partial_ok": False,
    },
    {
        "name": "React Dashboard",
        "files": [
            "dashboard/src/App.jsx",
            "dashboard/src/services/api.js",
            "dashboard/src/data/mockData.js",
        ],
        "partial_ok": True,
        "note": "mock data",
    },
    {
        "name": "Snowflake SQL",
        "files": [
            "snowflake/01_schema.sql",
            "snowflake/02_seed_data.sql",
            "snowflake/03_dynamic_tables.sql",
        ],
        "partial_ok": False,
    },
    {
        "name": "Trigger Listener",
        "files": [
            "ingestion/trigger_listener.py",
        ],
        "partial_ok": False,
    },
    {
        "name": "Backend API",
        "files": [
            "api.py",
        ],
        "partial_ok": False,
        "note": "for React live data",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def exists(path: str) -> bool:
    return (ROOT / path).exists()


def status_icon(component: dict) -> str:
    found = [f for f in component["files"] if exists(f)]
    total = len(component["files"])
    if len(found) == total:
        note = f" ({component['note']})" if component.get("note") else ""
        return f"✅ Done{note}"
    elif found and component.get("partial_ok"):
        note = f" ({component['note']})" if component.get("note") else ""
        return f"🔶 Partial{note}"
    elif found:
        return f"🔶 Partial ({len(found)}/{total} files)"
    else:
        return "❌ Missing"


def short_file_list(component: dict) -> str:
    names = [Path(f).name for f in component["files"]]
    return ", ".join(names[:3]) + (", ..." if len(names) > 3 else "")


# ── Status table ──────────────────────────────────────────────────────────────

def build_status_table() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "## Status Dashboard",
        "",
        "| Component | Key Files | Status |",
        "|-----------|-----------|--------|",
    ]
    for c in COMPONENTS:
        lines.append(f"| {c['name']} | {short_file_list(c)} | {status_icon(c)} |")
    lines.append("")
    lines.append(f"_Last updated: {now} by scripts/gen_architecture.py_")
    return "\n".join(lines)


# ── Directory tree ────────────────────────────────────────────────────────────

FILE_DESCRIPTIONS = {
    "agents/manager.py":               "← ENTRY POINT: run_incident_crew()",
    "agents/ag1_detector.py":          "Classify severity + blast radius",
    "agents/ag2_investigator.py":      "3-source root cause investigation",
    "agents/ag5_validator.py":         "Adversarial judge (APPROVE|DEBATE)",
    "agents/crew.py":                  "CrewAI Crew factory",
    "tools/query_snowflake.py":        "Generic SELECT (used by all agents)",
    "tools/search_runbooks.py":        "Cortex Search on RAW.RUNBOOKS",
    "tools/find_similar_incidents.py": "CORTEX.SIMILARITY on RAW.PAST_INCIDENTS",
    "tools/composio_actions.py":       "Slack + GitHub via Composio SDK",
    "tools/idempotency.py":            "SHA256 dedup before any external action",
    "utils/snowflake_conn.py":         "get_connection(), run_query(), run_dml()",
    "utils/snowflake_llm.py":          "SnowflakeCortexLLM wrapper (BaseChatModel)",
    "snowflake/01_schema.sql":         "DDL: RAW.*, AI.*, ANALYTICS.*",
    "snowflake/02_seed_data.sql":      "Runbooks, past incidents, sample metrics",
    "snowflake/03_dynamic_tables.sql": "ANALYTICS.METRIC_DEVIATIONS (z-score)",
    "ingestion/trigger_listener.py":   "Composio WebSocket → run_incident_crew()",
    "dashboard/src/services/api.js":   "Toggle VITE_USE_LIVE_DATA for real data",
    "dashboard/src/data/mockData.js":  "Offline demo data",
    "api.py":                          "FastAPI backend (for React live data)",
    "CLAUDE.md":                       "Claude Code auto-loads this every session",
    "ARCHITECTURE.md":                 "This file — auto-updated by hooks",
    "scripts/gen_architecture.py":     "Auto-updates this file",
    "requirements.txt":                "",
    "test_agent.py":                   "python test_agent.py [snowflake|agents]",
    ".env":                            "Credentials",
}

FOLDER_STATUS = {
    "agents":     lambda: "✅" if exists("agents/manager.py") else "❌",
    "tools":      lambda: "✅" if exists("tools/query_snowflake.py") else "❌",
    "utils":      lambda: "✅" if exists("utils/snowflake_conn.py") else "❌",
    "snowflake":  lambda: "✅" if exists("snowflake/01_schema.sql") else "❌ NOT CREATED (P1 task)",
    "ingestion":  lambda: "✅" if exists("ingestion/trigger_listener.py") else "❌ NOT CREATED (P3 task)",
    "dashboard":  lambda: "✅" if exists("dashboard/src/App.jsx") else "❌",
}


def build_file_tree() -> str:
    lines = ["```", "IncidentDNA/"]

    def icon(path: str) -> str:
        return "✅" if exists(path) else "❌"

    def desc(path: str) -> str:
        d = FILE_DESCRIPTIONS.get(path, "")
        return f"  {d}" if d else ""

    # agents/
    folder_st = FOLDER_STATUS["agents"]()
    lines.append(f"├── agents/                     {folder_st}")
    for f in ["agents/manager.py", "agents/ag1_detector.py", "agents/ag2_investigator.py",
              "agents/ag5_validator.py", "agents/crew.py"]:
        name = Path(f).name
        lines.append(f"│   ├── {name:<30}{desc(f)}")

    # tools/
    folder_st = FOLDER_STATUS["tools"]()
    lines.append(f"│")
    lines.append(f"├── tools/                      {folder_st}")
    for f in ["tools/query_snowflake.py", "tools/search_runbooks.py",
              "tools/find_similar_incidents.py", "tools/composio_actions.py",
              "tools/idempotency.py"]:
        name = Path(f).name
        lines.append(f"│   ├── {name:<30}{desc(f)}")

    # utils/
    folder_st = FOLDER_STATUS["utils"]()
    lines.append(f"│")
    lines.append(f"├── utils/                      {folder_st}")
    for f in ["utils/snowflake_conn.py", "utils/snowflake_llm.py"]:
        name = Path(f).name
        lines.append(f"│   ├── {name:<30}{desc(f)}")

    # snowflake/
    folder_st = FOLDER_STATUS["snowflake"]()
    lines.append(f"│")
    lines.append(f"├── snowflake/                  {folder_st}")
    for f in ["snowflake/01_schema.sql", "snowflake/02_seed_data.sql",
              "snowflake/03_dynamic_tables.sql"]:
        name = Path(f).name
        mark = icon(f)
        lines.append(f"│   ├── {name:<30}{mark}{desc(f)}")

    # ingestion/
    folder_st = FOLDER_STATUS["ingestion"]()
    lines.append(f"│")
    lines.append(f"├── ingestion/                  {folder_st}")
    f = "ingestion/trigger_listener.py"
    mark = icon(f)
    lines.append(f"│   └── trigger_listener.py         {mark}{desc(f)}")

    # dashboard/
    folder_st = FOLDER_STATUS["dashboard"]()
    lines.append(f"│")
    lines.append(f"├── dashboard/                  {folder_st} (mock data)")
    lines.append(f"│   └── src/")
    lines.append(f"│       ├── pages/              8 pages: Overview, Incidents, Releases...")
    for f in ["dashboard/src/services/api.js", "dashboard/src/data/mockData.js"]:
        name = Path(f).name
        lines.append(f"│       ├── {name:<26}{desc(f)}")

    # root files
    lines.append(f"│")
    for f in ["CLAUDE.md", "ARCHITECTURE.md", "scripts/gen_architecture.py",
              "requirements.txt", "test_agent.py", ".env"]:
        mark = "✅" if exists(f) else "❌"
        name = Path(f).name
        d = desc(f)
        lines.append(f"├── {name:<35}{mark}{d}")

    lines.append("```")
    return "\n".join(lines)


# ── Replace section between markers ──────────────────────────────────────────

def replace_section(content: str, start_marker: str, end_marker: str, new_body: str) -> str:
    pattern = rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
    replacement = f"{start_marker}\n{new_body}\n{end_marker}"
    result, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        print(f"  ⚠️  Marker not found: {start_marker}")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not ARCH_FILE.exists():
        print(f"❌ {ARCH_FILE} not found — run from project root")
        return

    content = ARCH_FILE.read_text()

    # Update status table
    content = replace_section(
        content,
        "<!-- STATUS_START -->",
        "<!-- STATUS_END -->",
        build_status_table(),
    )

    # Update file tree
    content = replace_section(
        content,
        "<!-- FILES_START -->",
        "<!-- FILES_END -->",
        build_file_tree(),
    )

    ARCH_FILE.write_text(content)
    print(f"✅ ARCHITECTURE.md updated — {datetime.now().strftime('%H:%M:%S')}")

    # Print quick summary
    for c in COMPONENTS:
        print(f"   {status_icon(c):30} {c['name']}")


if __name__ == "__main__":
    main()
