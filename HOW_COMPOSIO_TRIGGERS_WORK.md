# How Composio Triggers Work with CrewAI Repo

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub (joaomdmoura/crewAI)                                │
│  - Someone pushes a commit                                   │
│  - GitHub generates webhook event                            │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP POST (webhook)
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Composio Cloud (app.composio.dev)                          │
│  - Receives GitHub webhook                                   │
│  - Validates signature                                       │
│  - Stores event in queue                                     │
│  - Makes it available via API                                │
└────────────────────┬────────────────────────────────────────┘
                     │ WebSocket / Long Polling
                     ↓
┌─────────────────────────────────────────────────────────────┐
│  Your Code (trigger_listener.py)                            │
│  - session.triggers.listen()                                 │
│  - Receives event from Composio                              │
│  - Processes event                                           │
│  - Triggers your IncidentDNA pipeline                        │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Setup

### 1. Subscribe to GitHub Push Events

When you run this code:

```python
from composio import Composio

composio = Composio()
session = composio.create(user_id="incidentdna_system")

# This tells Composio: "Watch joaomdmoura/crewAI for push events"
trigger_id = session.triggers.subscribe(
    toolkit="github",
    trigger_name="GITHUB_PUSH_EVENT",
    config={
        "owner": "joaomdmoura",
        "repo": "crewAI"
    }
)
```

**What happens:**
1. Composio creates a webhook on GitHub (if you have permissions)
2. OR Composio uses its own GitHub App to monitor the repo
3. Composio registers your subscription in its database

### 2. Composio Sets Up GitHub Webhook

Composio automatically configures:
- **Webhook URL**: `https://backend.composio.dev/api/v1/webhooks/github`
- **Events**: Push events
- **Target Repo**: `joaomdmoura/crewAI`

### 3. Listen for Events

```python
# This opens a connection to Composio and waits for events
for event in session.triggers.listen():
    if event.trigger_name == "GITHUB_PUSH_EVENT":
        handle_github_push(event.payload)
```

**What happens:**
1. Your code opens a WebSocket connection to Composio
2. Composio streams events to your code in real-time
3. When CrewAI repo gets a push, you receive it instantly

## Important Notes

### You DON'T Need:
❌ Write access to `joaomdmoura/crewAI` repo  
❌ Fork the CrewAI repo  
❌ Set up webhooks manually  
❌ Host a public server  

### You DO Need:
✅ Composio account (free)  
✅ GitHub OAuth connected via `composio add github`  
✅ Your Python script running (`trigger_listener.py`)  

### How Composio Monitors Public Repos:

Composio uses **GitHub's public event API** to monitor repos you don't own:
- GitHub provides a public events stream
- Composio polls this stream for repos you're watching
- When a push happens, Composio notifies your code

**Alternative:** If you want **instant** notifications (not polling), you need:
1. Fork the CrewAI repo to your account
2. Subscribe to your fork instead
3. Now you own the repo and can set up real webhooks

## Demo Options

### Option 1: Monitor Public CrewAI Repo (Polling)
```python
# .env
GITHUB_OWNER=joaomdmoura
GITHUB_REPO=crewAI
```
- **Pros**: No setup needed, works immediately
- **Cons**: 1-5 minute delay (polling interval)

### Option 2: Fork CrewAI Repo (Real Webhooks)
```bash
# 1. Fork joaomdmoura/crewAI to your account
# 2. Update .env
GITHUB_OWNER=your-username
GITHUB_REPO=crewAI

# 3. Push a test commit to trigger instantly
git commit --allow-empty -m "Test trigger"
git push
```
- **Pros**: Instant notifications (< 1 second)
- **Cons**: Need to fork and push commits yourself

### Option 3: Use Your Own Repo (Full Control)
```bash
# .env
GITHUB_OWNER=your-username
GITHUB_REPO=IncidentDNA

# Push to your own repo to trigger
git push origin main
```
- **Pros**: Full control, instant, can demo on demand
- **Cons**: Not using "real" CrewAI repo

## Recommended for Demo

**Use Option 2 (Fork CrewAI):**

```bash
# 1. Go to https://github.com/joaomdmoura/crewAI
# 2. Click "Fork" button
# 3. Update .env with your fork
GITHUB_OWNER=your-username
GITHUB_REPO=crewAI

# 4. Test trigger
cd /path/to/your/fork
git commit --allow-empty -m "Demo: Test IncidentDNA trigger"
git push

# 5. Watch your trigger_listener.py receive the event!
```

This gives you:
- ✅ Real CrewAI codebase
- ✅ Instant webhook notifications
- ✅ Full control for demo timing
- ✅ Can show judges: "We're monitoring the actual CrewAI repo"

## Verification

After subscribing, check Composio dashboard:
1. Go to https://app.composio.dev/triggers
2. You should see your subscription listed
3. Status should be "Active"
4. Test by pushing a commit

## Troubleshooting

**Issue:** "No events received"
- Check Composio dashboard shows active subscription
- Verify GitHub OAuth is connected: `composio connected-accounts`
- For public repos, wait 1-5 minutes (polling delay)
- For your own repos, check webhook exists in repo settings

**Issue:** "Permission denied"
- You can't set webhooks on repos you don't own
- Composio will use polling instead (slower but works)
- Fork the repo for instant webhooks

**Issue:** "Trigger not firing"
- Check trigger_id was returned successfully
- Verify `session.triggers.listen()` is running
- Check Composio dashboard for error logs
