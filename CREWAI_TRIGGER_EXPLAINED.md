# How We Trigger on CrewAI Repository

## The Magic Line

In `ingestion/trigger_listener.py`, this is the key code that watches the CrewAI repo:

```python
# Subscribe to GitHub push events on CrewAI repo
trigger_id = session.triggers.subscribe(
    toolkit="github",
    trigger_name="GITHUB_PUSH_EVENT",
    config={
        "owner": "joaomdmoura",      # ← CrewAI repo owner
        "repo": "crewAI"              # ← CrewAI repo name
    }
)
```

## What This Does

### 1. Composio Registers Your Interest
When you run `session.triggers.subscribe()`:
- Composio says: "This user wants to know about pushes to `joaomdmoura/crewAI`"
- Composio starts monitoring that repo using GitHub's API
- You get a `trigger_id` back (like a subscription receipt)

### 2. Composio Watches the Repo
Composio has two ways to watch repos:

**Option A: Public Repo Polling (What we're using)**
```
Composio → GitHub API → "Any new commits on joaomdmoura/crewAI?"
         ← GitHub API ← "Yes! Commit abc123 just pushed"
Composio → Your code → "Here's the event!"
```
- Checks every 1-5 minutes
- Works for ANY public repo
- No permissions needed

**Option B: Webhook (If you own the repo)**
```
GitHub → Webhook → Composio → Your code
```
- Instant (< 1 second)
- Requires repo ownership
- More reliable

### 3. Your Code Receives Events
```python
# This line blocks and waits for events
for event in session.triggers.listen():
    if event.trigger_name == "GITHUB_PUSH_EVENT":
        handle_github_push(event.payload)
```

When someone pushes to CrewAI repo:
1. Composio detects it
2. Sends event to your code
3. Your `handle_github_push()` function runs
4. Pipeline starts!

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  CrewAI Repository (joaomdmoura/crewAI)                     │
│  https://github.com/joaomdmoura/crewAI                      │
│                                                              │
│  Someone pushes a commit:                                    │
│  $ git push origin main                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ GitHub stores commit
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  GitHub Public Events API                                    │
│  https://api.github.com/repos/joaomdmoura/crewAI/events     │
│                                                              │
│  Returns: {                                                  │
│    "type": "PushEvent",                                      │
│    "repo": "joaomdmoura/crewAI",                            │
│    "payload": {...}                                          │
│  }                                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Composio polls every 1-5 min
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Composio Cloud (app.composio.dev)                          │
│                                                              │
│  1. Polls GitHub API for new events                          │
│  2. Finds new PushEvent on joaomdmoura/crewAI               │
│  3. Checks: "Who subscribed to this repo?"                   │
│  4. Finds your subscription (trigger_id)                     │
│  5. Queues event for delivery                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ WebSocket / Long Polling
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Your Code (trigger_listener.py)                            │
│                                                              │
│  session.triggers.listen() ← Receives event                 │
│         ↓                                                    │
│  handle_github_push(event.payload)                          │
│         ↓                                                    │
│  1. Insert RAW.DEPLOY_EVENTS                                │
│  2. Inject synthetic spike → RAW.METRICS                    │
│  3. Query ANALYTICS.METRIC_DEVIATIONS                       │
│  4. If anomaly → Insert AI.ANOMALY_EVENTS                   │
│  5. Trigger CrewAI agents (Person 2's code)                 │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Your `.env` file controls which repo to watch:

```bash
# Watch the official CrewAI repo
GITHUB_OWNER=joaomdmoura
GITHUB_REPO=crewAI
```

Change these to watch a different repo:

```bash
# Watch your own fork
GITHUB_OWNER=your-username
GITHUB_REPO=crewAI

# Or watch any other repo
GITHUB_OWNER=openai
GITHUB_REPO=openai-python
```

## Why This Works for CrewAI Repo

1. **CrewAI is public** - Anyone can read its events via GitHub API
2. **Composio has GitHub access** - You connected via `composio add github`
3. **No special permissions needed** - You're just reading public data
4. **Composio does the heavy lifting** - Polling, event parsing, delivery

## What Happens When CrewAI Gets a Commit

Let's say someone pushes to CrewAI repo at 2:00 PM:

```
2:00:00 PM - Developer pushes to joaomdmoura/crewAI
2:00:01 PM - GitHub stores commit
2:01:00 PM - Composio polls GitHub API (1 min later)
2:01:01 PM - Composio finds new PushEvent
2:01:02 PM - Composio sends event to your code
2:01:03 PM - Your trigger_listener.py receives event
2:01:04 PM - handle_github_push() starts processing
2:01:05 PM - Deploy event inserted into Snowflake
2:01:06 PM - Synthetic spike injected
2:01:07 PM - Anomaly detected
2:01:08 PM - CrewAI agents triggered (Person 2's code)
2:01:30 PM - GitHub issue created on CrewAI repo
2:01:31 PM - Slack alert posted
```

**Total time: ~90 seconds from commit to alert**

## Testing Without Waiting for Real Commits

You don't have to wait for someone to push to CrewAI. Test immediately:

### Option 1: Simulate Event
```python
# test_crewai_trigger.py
from ingestion.trigger_listener import handle_github_push

# Fake a CrewAI commit
fake_event = {
    "repository": {"name": "crewAI"},
    "after": "abc1234567",
    "pusher": {"name": "test-user"},
    "ref": "refs/heads/main",
    "head_commit": {
        "message": "Test commit for IncidentDNA demo"
    }
}

handle_github_push(fake_event)
```

Run: `python test_crewai_trigger.py`

### Option 2: Fork CrewAI
```bash
# 1. Fork joaomdmoura/crewAI to your account
# 2. Update .env
GITHUB_OWNER=your-username
GITHUB_REPO=crewAI

# 3. Push empty commit to trigger
git commit --allow-empty -m "Test IncidentDNA trigger"
git push
```

### Option 3: Use Your Own Repo
```bash
# .env
GITHUB_OWNER=your-username
GITHUB_REPO=IncidentDNA

# Push to trigger
git push origin main
```

## Verification Steps

1. **Check subscription is active:**
```bash
python test_setup.py
```

2. **Start listener:**
```bash
python ingestion/trigger_listener.py
```

You should see:
```
============================================================
IncidentDNA Trigger Listener Starting...
============================================================
✓ Subscribed to GitHub push events (trigger_id: xxx)
Waiting for events...
```

3. **Trigger an event** (use one of the test methods above)

4. **Watch the output:**
```
[COMPOSIO TRIGGER] GitHub push event received!
  Repository: crewAI
  Commit: abc1234
  Pusher: test-user
  Branch: main

[STEP 1] Inserting deploy event into RAW.DEPLOY_EVENTS
  ✓ Deploy event created: deploy_abc1234

[STEP 2] Injecting synthetic metric spike
  ✓ Spike injected

[STEP 3] Checking for anomalies
  ✓ Found 2 anomalies

[STEP 4] Triggering incident pipeline
  ✓ Pipeline triggered
```

5. **Check Snowflake:**
```sql
-- See the deploy event
SELECT * FROM RAW.DEPLOY_EVENTS ORDER BY deployed_at DESC LIMIT 1;

-- See the anomaly
SELECT * FROM AI.ANOMALY_EVENTS ORDER BY detected_at DESC LIMIT 1;
```

## Summary

**You ARE triggering on the real CrewAI repository!**

- ✅ Watching: `joaomdmoura/crewAI`
- ✅ Method: Composio polls GitHub API
- ✅ Delay: 1-5 minutes (acceptable for demo)
- ✅ No permissions needed
- ✅ Works right now

**To make it instant:** Fork the repo and use webhooks (optional).

**To test now:** Use the simulation script (no waiting needed).
