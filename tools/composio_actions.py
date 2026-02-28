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


def _execute_with_retry(action_name: str, payload: dict) -> dict:
    """Execute a Composio action with retry logic and exponential backoff.
    Uses Composio SDK v1.0.0-rc2 API: client.tools.execute(slug, arguments, user_id=...).
    """
    client = _get_client()
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            result = client.tools.execute(
                slug=action_name,
                arguments=payload,
                user_id=COMPOSIO_USER_ID,
                dangerously_skip_version_check=True,
            )
            # SDK returns a dict with 'successful', 'data', 'error' keys
            if isinstance(result, dict) and result.get("successful") is False:
                raise RuntimeError(result.get("error", "Composio action failed"))
            return result  # success
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
    evidence_sources: list[str] | None = None,
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

    blast_str = ", ".join(f"`{s}`" for s in blast_radius) if blast_radius else "None identified"
    evidence_str = ", ".join(evidence_sources) if evidence_sources else "metrics, logs"

    fix_lines = ""
    if fix_options:
        for i, fix in enumerate(fix_options[:3], 1):
            title = fix.get("title", "N/A")
            risk = fix.get("risk_level", "MEDIUM")
            cmds = fix.get("commands", [])
            cmd_str = f" | cmd: `{cmds[0]}`" if cmds else ""
            loc = fix.get("file", fix.get("location", ""))
            loc_str = f" | file: `{loc}`" if loc else ""
            fix_lines += f"  {i}. *{title}* (risk: {risk}{cmd_str}{loc_str})\n"

    message = (
        f"*[{severity}] INCIDENT DETECTED — IncidentDNA*\n"
        f"---\n"
        f"*Service:* `{service}`\n"
        f"*Severity:* `{severity}`\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Blast Radius:* {blast_str}\n"
        f"*Evidence:* {evidence_str}\n"
    )
    if fix_lines:
        message += f"*Recommended Fixes:*\n{fix_lines}"
    message += (
        f"---\n"
        f"*Event ID:* `{event_id}`\n"
        f"*Pipeline:* Autonomous investigation in progress. Agents evaluating fix options."
    )

    channel = os.getenv("SLACK_CHANNEL", "team-spartans").lstrip("#")
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
    blast_radius: list[str] | None = None,
    fix_options: list[dict] | None = None,
    evidence_sources: list[str] | None = None,
    confidence: float = 0.0,
    threshold_decision: str = "",
    rule_applied: str = "",
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
    owner, repo_name = (repo.split("/") + [""])[:2]

    blast_str = ", ".join(f"`{s}`" for s in blast_radius) if blast_radius else "None identified"
    evidence_str = ", ".join(f"`{s}`" for s in evidence_sources) if evidence_sources else "`metrics`, `logs`"

    # Fix options table
    fix_table = ""
    if fix_options:
        fix_table = "\n| # | Fix | Risk | Commands | File / Location |\n|---|-----|------|----------|-----------------|\n"
        for i, fo in enumerate(fix_options[:3], 1):
            t = fo.get("title", "N/A")
            r = fo.get("risk_level", "MEDIUM")
            c = ", ".join(fo.get("commands", [])) or "-"
            loc = fo.get("file", fo.get("location", "-"))
            fix_table += f"| {i} | **{t}** | {r} | `{c}` | `{loc}` |\n"

    title = f"[{severity}] {service} — {root_cause[:70]}"
    body = f"""## Incident Report

> Auto-generated by **IncidentDNA** autonomous incident pipeline.

### Summary

| Field | Value |
|---|---|
| **Event ID** | `{event_id}` |
| **Service** | `{service}` |
| **Severity** | `{severity}` |
| **Confidence** | `{confidence:.0%}` |
| **Decision** | `{threshold_decision}` |
| **Rule** | `{rule_applied}` |
| **Blast Radius** | {blast_str} |
| **Evidence** | {evidence_str} |

### Root Cause Analysis

{root_cause}

### Recommended Fix

{fix}
{fix_table}
### Resolution Checklist

- [ ] Root cause confirmed by on-call engineer
- [ ] Fix verified in staging environment
- [ ] Fix deployed to production
- [ ] Service health metrics returned to baseline
- [ ] Blast radius services confirmed healthy
- [ ] Post-mortem document created
- [ ] Runbook updated if applicable

### Diagnostic Commands

```bash
# Check service health
curl -s http://{service}:8080/health | jq .

# Tail recent logs
kubectl logs -l app={service} --tail=100 --since=15m

# Check error rate
snowsql -q "SELECT COUNT(*) FROM AI.METRICS WHERE service='{service}' AND metric='error_rate' AND ts > DATEADD(minute, -30, CURRENT_TIMESTAMP())"
```

---
Generated by IncidentDNA. Do not close until all checklist items are verified.
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
    evidence_sources: list[str] | None = None,
    rule_applied: str = "",
) -> str:
    """
    Post an AUTO-RESOLVED Slack alert. Used when the threshold engine decides AUTO_RESOLVE.
    """
    key = _idempotency_key("SLACK_AUTO_RESOLVED", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    blast_str = ", ".join(f"`{s}`" for s in blast_radius) if blast_radius else "None identified"
    evidence_str = ", ".join(evidence_sources) if evidence_sources else "metrics, logs"
    fix_desc = fix_options[0].get("title", "N/A") if fix_options else "N/A"
    fix_cmds = fix_options[0].get("commands", []) if fix_options else []
    fix_cmd_str = ", ".join(fix_cmds) if fix_cmds else "N/A"
    fix_loc = ""
    if fix_options:
        loc = fix_options[0].get("file", fix_options[0].get("location", ""))
        if loc:
            fix_loc = f"*File:* `{loc}`\n"

    message = (
        f"*[{severity}] AUTO-RESOLVED — `{service}`*\n"
        f"---\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Fix Applied:* {fix_desc}\n"
    )
    if fix_cmd_str != "N/A":
        message += f"*Commands Executed:* `{fix_cmd_str[:200]}`\n"
    if fix_loc:
        message += fix_loc
    message += (
        f"*Blast Radius:* {blast_str}\n"
        f"*Evidence:* {evidence_str}\n"
        f"---\n"
        f"*Confidence:* `{confidence:.0%}` | *MTTR:* `{mttr_seconds}s`\n"
        f"*Resolution Rule:* `{rule_applied}`\n"
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
    evidence_sources: list[str] | None = None,
    rule_applied: str = "",
) -> str:
    """
    Post a HUMAN_ESCALATION Slack alert with urgency-band formatting.
    """
    key = _idempotency_key("SLACK_ESCALATION", event_id)
    prev = _already_sent(key)
    if prev:
        return f"SKIPPED_DUPLICATE (previous: {prev})"

    blast_str = ", ".join(f"`{s}`" for s in blast_radius) if blast_radius else "None identified"
    evidence_str = ", ".join(evidence_sources) if evidence_sources else "metrics, logs"

    # Urgency-band formatting (no emojis)
    if urgency == "IMMEDIATE":
        header = f"*[CRITICAL] {incident_type} INCIDENT — Human Review Required*"
        status_line = "NO AUTO-ACTIONS TAKEN — awaiting human approval"
    elif urgency in ("HIGH", "HIGH_CONFIDENCE"):
        header = "*[HIGH] INCIDENT DETECTED — High Confidence*"
        status_line = "Recommended fix ready — awaiting human approval before execution"
    elif urgency == "MEDIUM_CONFIDENCE":
        header = "*[MEDIUM] INCIDENT DETECTED — Under Investigation*"
        status_line = "Multiple hypotheses identified — human triage needed"
    else:
        header = "*[LOW] INCIDENT DETECTED — Low Confidence*"
        status_line = "Root cause unclear — immediate human investigation required"

    message = (
        f"*[{severity}]* {header}\n"
        f"---\n"
        f"*Service:* `{service}`\n"
        f"*Incident Type:* `{incident_type}`\n"
        f"*Root Cause:* {root_cause}\n"
        f"*Blast Radius:* {blast_str}\n"
        f"*Confidence:* `{confidence:.0%}`\n"
        f"*Evidence:* {evidence_str}\n"
    )

    if fix_options:
        for i, fo in enumerate(fix_options[:2], 1):
            fix_title = fo.get("title", "N/A")
            fix_risk = fo.get("risk_level", "MEDIUM")
            cmds = fo.get("commands", [])
            cmd_str = f" | cmd: `{cmds[0]}`" if cmds else ""
            loc = fo.get("file", fo.get("location", ""))
            loc_str = f" | file: `{loc}`" if loc else ""
            message += f"*Fix Option {i}:* {fix_title} (risk: {fix_risk}{cmd_str}{loc_str})\n"

    message += (
        f"---\n"
        f"*Resolution Rule:* `{rule_applied}`\n"
        f"*Status:* {status_line}\n"
        f"*Event ID:* `{event_id}`"
    )

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
        f"*[CI PASS] Fix Verified — `{service}`*\n"
        f"---\n"
        f"*Workflow:* `{workflow}`\n"
        f"*Branch:* `{branch}` | *Commit:* `{sha}`\n"
        f"*Result:* All checks passed. Incident fix confirmed by CI pipeline.\n"
        f"*Run URL:* {url}\n"
        f"---\n"
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

    message = (
        f"*[CI FAIL] Pipeline Failure — `{service}`*\n"
        f"---\n"
        f"*Workflow:* `{workflow}`\n"
        f"*Conclusion:* `{conclusion.upper()}`\n"
        f"*Branch:* `{branch}` | *Commit:* `{sha}`\n"
        f"*Action:* IncidentDNA autonomous agents have been triggered. Investigation in progress.\n"
        f"*Run URL:* {url}\n"
        f"---\n"
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
