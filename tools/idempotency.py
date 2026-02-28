import json
import hashlib
from utils.snowflake_conn import run_dml, run_query


def safe_execute(
    action_type: str,
    event_id: str,
    payload: dict,
    executor_fn=None,
) -> str:
    """
    Idempotent action executor.

    Before executing any external action (Slack, GitHub, etc.):
      1. Derives a deterministic idempotency key from action_type + event_id.
      2. Checks AI.ACTIONS — skips if already executed.
      3. Records intent as PENDING before executing.
      4. Calls executor_fn(payload) if provided.
      5. Updates status to SENT or FAILED.

    Returns: 'SENT' | 'SKIPPED_DUPLICATE' | 'FAILED: <reason>'
    """
    key = hashlib.sha256(f"{action_type}:{event_id}".encode()).hexdigest()[:32]

    existing = run_query(
        "SELECT status FROM AI.ACTIONS WHERE idempotency_key = %s",
        (key,),
    )
    if existing:
        return f"SKIPPED_DUPLICATE (previous status: {existing[0]['STATUS']})"

    run_dml(
        """INSERT INTO AI.ACTIONS
               (event_id, action_type, idempotency_key, payload, status)
           VALUES (%s, %s, %s, PARSE_JSON(%s), 'PENDING')""",
        (event_id, action_type, key, json.dumps(payload)),
    )

    try:
        if executor_fn:
            executor_fn(payload)
        run_dml(
            "UPDATE AI.ACTIONS SET status = 'SENT' WHERE idempotency_key = %s",
            (key,),
        )
        return "SENT"
    except Exception as e:
        run_dml(
            "UPDATE AI.ACTIONS SET status = 'FAILED' WHERE idempotency_key = %s",
            (key,),
        )
        return f"FAILED: {e}"
