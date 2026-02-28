"""
Composio actions — Slack alert + GitHub issue.
Uses the new Composio SDK (composio package, session-based).

Includes retry logic (up to 2 retries with exponential backoff) and
fallback mode: if Composio is unavailable, alerts are logged to
AI.ACTIONS with status FALLBACK_LOGGED so they can be sent manually.

Setup (one-time, before running):
  1. pip install composio
  2. Set COMPOSIO_API_KEY in .env (get from https://app.composio.dev/settings)
  3. Run: python scripts/setup_composio.py (authenticates GitHub + Slack)
"""

import os
import json
import time
import hashlib
from composio import Composio
from dotenv import load_dotenv
from utils.snowflake_conn import run_dml, run_query

load_dotenv()

# Fixed user ID for this agent — must match the user that authenticated
# GitHub and Slack in the Composio dashboard
COMPOSIO_USER_ID = "pg-test-a6c32032-f3c5-43d2-9090-e16ffbd46f0d"

MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 2  # seconds

_client: Composio | None = None


def _get_client() -> Composio:
    global _client
    if _client is None:
        _client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
    return _client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _idempotency_key(action_type: str, event_id: str) -> str:
    return hashlib.sha256(f"{action_type}:{event_id}".encode()).hexdigest()[:32]


def _record_action(event_id: str, action_type: str, key: str, payload: dict) -> None:
    run_dml(
        """INSERT INTO AI.ACTIONS
               (event_id, action_type, idempotency_key, payload, status)
           SELECT %s, %s, %s, PARSE_JSON(%s), 'PENDING'""",
        (event_id, action_type, key, json.dumps(payload)),
    )


def _update_status(key: str, status: str) -> None:
    run_dml(
        "UPDATE AI.ACTIONS SET status = %s WHERE idempotency_key = %s",
        (status, key),
    )


def _already_sent(key: str) -> str | None:
    rows = run_query(
        "SELECT status FROM AI.ACTIONS WHERE idempotency_key = %s", (key,)
    )
    return rows[0]["STATUS"] if rows else None


def _execute_with_retry(action_name: str, payload: dict) -> None:
    """Execute a Composio action with retry logic and exponential backoff."""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            _get_client().tools.execute(
                action_name,
                payload,
                user_id=COMPOSIO_USER_ID,
                dangerously_skip_version_check=True,
            )
            return  # success
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                print(f"[COMPOSIO] Retry {attempt + 1}/{MAX_RETRIES} for {action_name} in {wait}s: {e}")
                time.sleep(wait)
    raise last_error  # all retries exhausted


def _fallback_log(event_id: str, action_type: str, key: str, payload: dict, error: str) -> str:
    """
    Fallback: log the alert to Snowflake AI.ACTIONS with FALLBACK_LOGGED status.
    This ensures no alert is lost — operators can review and send manually.
    """
    _update_status(key, "FALLBACK_LOGGED")
    print(f"[COMPOSIO] FALLBACK: {action_type} for {event_id} logged to AI.ACTIONS (Composio unavailable: {error})")
    return f"FALLBACK_LOGGED (Composio unavailable: {error})"


# ---------------------------------------------------------------------------
# Public actions
# ---------------------------------------------------------------------------

def post_slack_alert(
    event_id: str,
    service: str,
    severity: str,
    root_cause: str,
    blast_radius: list[str] | None = None,
    fix_options: list[dict] | None = None,
) -> str:
    """
    Post a Slack incident alert via Composio.
    Idempotent — safe to call multiple times for the same event.
    Retries up to 2 times with exponential backoff.
    Falls back to Snowflake logging if Composio is unavailable.
    Returns: 'SENT' | 'SKIPPED_DUPLICATE (...)' | 'FALLBACK_LOGGED (...)' | 'FAILED: ...'
    """
    key = _idempotency_key("SLACK_ALERT", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    severity_emoji = {"P1": "\U0001f6a8", "P2": "\u26a0\ufe0f", "P3": "\u2139\ufe0f"}.get(severity, "\U0001f514")

    # Build blast radius section
    blast_str = ", ".join(blast_radius) if blast_radius else "None identified"

    # Build fix options section
    fix_lines = ""
    if fix_options:
        num_emojis = ["1\ufe0f\u20e3", "2\ufe0f\u20e3", "3\ufe0f\u20e3"]
        for i, fix in enumerate(fix_options[:3], 0):
            title = fix.get("title", "N/A")
            risk = fix.get("risk_level", "MEDIUM")
            fix_lines += f"  {num_emojis[i]} {title} (risk: {risk})\n"

    message = (
        f"{severity_emoji} *[{severity}] IncidentDNA Alert*\n"
        f"*Service:* {service}\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Blast Radius:* {blast_str}\n"
    )
    if fix_lines:
        message += f"*Fix Options:*\n{fix_lines}"
    message += (
        f"*Event ID:* `{event_id}`\n"
        f"_Autonomous response in progress..._"
    )

    channel = os.getenv("SLACK_CHANNEL", "#incidents").lstrip("#")  # API rejects '#' prefix
    payload = {"channel": channel, "markdown_text": message}

    _record_action(event_id, "SLACK_ALERT", key, payload)
    try:
        _execute_with_retry("SLACK_SEND_MESSAGE", payload)
        _update_status(key, "SENT")
        return "SENT"
    except Exception as e:
        return _fallback_log(event_id, "SLACK_ALERT", key, payload, str(e))


def create_github_issue(
    event_id: str,
    service: str,
    severity: str,
    root_cause: str,
    fix: str,
) -> str:
    """
    Create a GitHub issue via Composio.
    Idempotent — safe to call multiple times for the same event.
    Retries up to 2 times with exponential backoff.
    Falls back to Snowflake logging if Composio is unavailable.
    Returns: 'SENT' | 'SKIPPED_DUPLICATE (...)' | 'FALLBACK_LOGGED (...)' | 'FAILED: ...'
    """
    key = _idempotency_key("GITHUB_ISSUE", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    repo = os.getenv("GITHUB_REPO", "")
    owner, repo_name = (repo.split("/") + [""])[:2]  # split "owner/repo"

    title = f"[{severity}] {service} — {root_cause[:70]}"
    body = f"""## IncidentDNA — Automated Incident Report

| Field | Value |
|-------|-------|
| **Event ID** | `{event_id}` |
| **Service** | {service} |
| **Severity** | {severity} |

### Root Cause
{root_cause}

### Recommended Fix
{fix}

### Resolution Checklist
- [ ] Root cause confirmed by on-call engineer
- [ ] Fix applied
- [ ] Service health restored
- [ ] Post-mortem scheduled

---
*Auto-generated by IncidentDNA. Do not close until resolution is confirmed.*
"""
    payload = {"owner": owner, "repo": repo_name, "title": title, "body": body}

    _record_action(event_id, "GITHUB_ISSUE", key, payload)
    try:
        _execute_with_retry("GITHUB_CREATE_AN_ISSUE", payload)
        _update_status(key, "SENT")
        return "SENT"
    except Exception as e:
        return _fallback_log(event_id, "GITHUB_ISSUE", key, payload, str(e))
