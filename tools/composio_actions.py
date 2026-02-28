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
from typing import Any
from dotenv import load_dotenv
from utils.snowflake_conn import run_dml, run_query

load_dotenv()
os.environ.setdefault("COMPOSIO_CACHE_DIR", "/tmp/composio-cache")

# Fixed user ID for this agent — must match the user that authenticated
# GitHub and Slack in the Composio dashboard
COMPOSIO_USER_ID = "pg-test-a6c32032-f3c5-43d2-9090-e16ffbd46f0d"

MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 2  # seconds

_client: Any | None = None


def _get_client():
    global _client
    if _client is None:
        from composio import Composio
        _client = Composio(api_key=os.getenv("COMPOSIO_API_KEY"))
    return _client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _idempotency_key(action_type: str, event_id: str) -> str:
    return hashlib.sha256(f"{action_type}:{event_id}".encode()).hexdigest()[:32]


def _existing_status(key: str) -> str | None:
    rows = run_query(
        "SELECT status FROM AI.ACTIONS WHERE idempotency_key = %s",
        (key,),
    )
    return rows[0]["STATUS"] if rows else None


def _record_action(event_id: str, action_type: str, key: str, payload: dict) -> None:
    existing = _existing_status(key)
    if existing in {"FAILED", "FALLBACK_LOGGED"}:
        run_dml(
            """UPDATE AI.ACTIONS
                  SET event_id = %s,
                      payload = PARSE_JSON(%s),
                      status = 'PENDING',
                      executed_at = CURRENT_TIMESTAMP()
                WHERE idempotency_key = %s""",
            (event_id, json.dumps(payload), key),
        )
        return

    if existing:
        return

    run_dml(
        """INSERT INTO AI.ACTIONS
               (event_id, action_type, idempotency_key, payload, status)
           SELECT %s, %s, %s, PARSE_JSON(%s), 'PENDING'""",
        (event_id, action_type, key, json.dumps(payload)),
    )


def _update_status(key: str, status: str) -> None:
    run_dml(
        """UPDATE AI.ACTIONS
              SET status = %s,
                  executed_at = CURRENT_TIMESTAMP()
            WHERE idempotency_key = %s""",
        (status, key),
    )


def _already_sent(key: str) -> str | None:
    """Returns SENT to skip duplicate. FAILED/FALLBACK return None so _record_action retries."""
    status = _existing_status(key)
    if status in {"FAILED", "FALLBACK_LOGGED"}:
        return None
    return status


def _execute_with_retry(action_name: str, payload: dict) -> None:
    """Execute a Composio action with retry logic and exponential backoff."""
    from composio import Action
    action = Action(action_name)
    entity = _get_client().get_entity(id=COMPOSIO_USER_ID)
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            entity.execute(action=action, params=payload)
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

    channel = os.getenv("SLACK_CHANNEL", "team-spartans").lstrip("#")  # strip '#' if present
    payload = {"channel": channel, "text": message}

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


# ---------------------------------------------------------------------------
# Threshold Engine — message variants
# ---------------------------------------------------------------------------

def post_slack_alert_auto_resolved(
    event_id: str,
    service: str,
    severity: str,
    root_cause: str,
    blast_radius: list[str] | None = None,
    fix_options: list[dict] | None = None,
    confidence: float = 0.0,
    mttr_seconds: int = 0,
) -> str:
    """
    Post an AUTO-RESOLVED Slack alert. Used when the threshold engine decides AUTO_RESOLVE.
    """
    key = _idempotency_key("SLACK_AUTO_RESOLVED", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    blast_str = ", ".join(blast_radius) if blast_radius else "None identified"
    fix_desc = fix_options[0]["title"] if fix_options else "N/A"
    fix_cmds = ", ".join(fix_options[0].get("commands", [])) if fix_options else "N/A"

    message = (
        f"\u2705 *AUTO-RESOLVED: {service}*\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Fix Applied:* {fix_desc}\n"
    )
    if fix_cmds and fix_cmds != "N/A":
        message += f"*Commands:* `{fix_cmds[:200]}`\n"
    message += (
        f"*Blast Radius:* {blast_str}\n"
        f"*Confidence:* {confidence:.0%} | *MTTR:* {mttr_seconds}s\n"
        f"*Status:* Resolved autonomously. No human intervention required.\n"
        f"*Event ID:* `{event_id}`"
    )

    channel = os.getenv("SLACK_CHANNEL", "team-spartans").lstrip("#")
    payload = {"channel": channel, "text": message}

    _record_action(event_id, "SLACK_AUTO_RESOLVED", key, payload)
    try:
        _execute_with_retry("SLACK_SEND_MESSAGE", payload)
        _update_status(key, "SENT")
        return "SENT"
    except Exception as e:
        return _fallback_log(event_id, "SLACK_AUTO_RESOLVED", key, payload, str(e))


def post_slack_alert_escalation(
    event_id: str,
    service: str,
    severity: str,
    root_cause: str,
    blast_radius: list[str] | None = None,
    fix_options: list[dict] | None = None,
    urgency: str = "MEDIUM_CONFIDENCE",
    incident_type: str = "PERFORMANCE",
    confidence: float = 0.0,
) -> str:
    """
    Post a HUMAN_ESCALATION Slack alert with urgency-band formatting.
    """
    key = _idempotency_key("SLACK_ESCALATION", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    blast_str = ", ".join(blast_radius) if blast_radius else "None identified"

    # Urgency-band formatting
    if urgency == "IMMEDIATE":
        emoji = "\U0001f6a8"
        header = f"*{incident_type} INCIDENT \u2014 Human Review Required*"
        status_line = f"\u26a0\ufe0f NO AUTO-ACTIONS TAKEN \u2014 awaiting human approval"
    elif urgency in ("HIGH", "HIGH_CONFIDENCE"):
        emoji = "\u26a0\ufe0f"
        header = f"*INCIDENT DETECTED (High Confidence)*"
        status_line = f"\u26a1 Recommended fix ready \u2014 awaiting human approval"
    elif urgency == "MEDIUM_CONFIDENCE":
        emoji = "\U0001f536"
        header = f"*INCIDENT DETECTED (Investigating)*"
        status_line = f"Multiple hypotheses \u2014 human triage needed"
    else:
        emoji = "\U0001f534"
        header = f"*INCIDENT DETECTED (Low Confidence)*"
        status_line = f"Root cause unclear \u2014 immediate human investigation required"

    message = (
        f"{emoji} *[{severity}]* {header}\n"
        f"*Service:* {service}\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Blast Radius:* {blast_str}\n"
        f"*Confidence:* {confidence:.0%}\n"
    )

    # Include fix recommendation for high-confidence escalations
    if fix_options and urgency in ("HIGH", "HIGH_CONFIDENCE", "IMMEDIATE"):
        fix_title = fix_options[0].get("title", "N/A")
        fix_risk = fix_options[0].get("risk_level", "MEDIUM")
        message += f"*Recommended Fix:* {fix_title} (risk: {fix_risk})\n"

    message += (
        f"*Status:* {status_line}\n"
        f"*Event ID:* `{event_id}`"
    )

    # Route security incidents to security channel if configured
    if incident_type == "SECURITY":
        channel = os.getenv("SLACK_SECURITY_CHANNEL", os.getenv("SLACK_CHANNEL", "team-spartans"))
    else:
        channel = os.getenv("SLACK_CHANNEL", "team-spartans")
    channel = channel.lstrip("#")

    payload = {"channel": channel, "text": message}

    _record_action(event_id, "SLACK_ESCALATION", key, payload)
    try:
        _execute_with_retry("SLACK_SEND_MESSAGE", payload)
        _update_status(key, "SENT")
        return "SENT"
    except Exception as e:
        return _fallback_log(event_id, "SLACK_ESCALATION", key, payload, str(e))


# ---------------------------------------------------------------------------
# CI Feedback Loop — success confirmation + failure re-alert
# ---------------------------------------------------------------------------

def post_slack_ci_confirmed(
    event_id: str,
    service: str,
    workflow: str,
    branch: str,
    sha: str,
    url: str,
) -> str:
    """
    Post a CI-confirmed Slack message when GitHub Actions passes after an incident fix.
    Uses a unique idempotency key per (event_id + sha) so it only fires once per commit.
    """
    key = _idempotency_key(f"SLACK_CI_CONFIRMED:{sha}", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    message = (
        f"\u2705 *CI CONFIRMED: Fix verified for {service}*\n"
        f"*Workflow:* {workflow}\n"
        f"*Branch:* {branch} | *Commit:* `{sha}`\n"
        f"*Status:* All checks passed — incident fix confirmed by CI\n"
        f"*Run:* {url}\n"
        f"*Event ID:* `{event_id}`"
    )

    channel = os.getenv("SLACK_CHANNEL", "team-spartans").lstrip("#")
    payload = {"channel": channel, "text": message}

    _record_action(event_id, "SLACK_CI_CONFIRMED", key, payload)
    try:
        _execute_with_retry("SLACK_SEND_MESSAGE", payload)
        _update_status(key, "SENT")
        return "SENT"
    except Exception as e:
        return _fallback_log(event_id, "SLACK_CI_CONFIRMED", key, payload, str(e))


def post_slack_ci_failure(
    event_id: str,
    service: str,
    workflow: str,
    branch: str,
    sha: str,
    conclusion: str,
    url: str,
) -> str:
    """
    Post a CI-failure Slack alert when GitHub Actions fails.
    Called directly from trigger_listener — the full pipeline also fires separately.
    """
    key = _idempotency_key("SLACK_CI_FAILURE", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    conclusion_emoji = {
        "failure":        "\u274c",
        "timed_out":      "\u23f0",
        "action_required": "\u26a0\ufe0f",
    }.get(conclusion, "\u274c")

    message = (
        f"{conclusion_emoji} *CI FAILURE: {service}*\n"
        f"*Workflow:* {workflow} — `{conclusion.upper()}`\n"
        f"*Branch:* {branch} | *Commit:* `{sha}`\n"
        f"*Action:* IncidentDNA is investigating — agents running now\n"
        f"*Run:* {url}\n"
        f"*Event ID:* `{event_id}`"
    )

    channel = os.getenv("SLACK_CHANNEL", "team-spartans").lstrip("#")
    payload = {"channel": channel, "text": message}

    _record_action(event_id, "SLACK_CI_FAILURE", key, payload)
    try:
        _execute_with_retry("SLACK_SEND_MESSAGE", payload)
        _update_status(key, "SENT")
        return "SENT"
    except Exception as e:
        return _fallback_log(event_id, "SLACK_CI_FAILURE", key, payload, str(e))
