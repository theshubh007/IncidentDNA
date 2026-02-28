# CrewAI + Composio Setup Guide

## Official Resources

**Composio CrewAI Provider:**
- Docs: https://docs.composio.dev/docs/providers/crewai
- GitHub: https://github.com/ComposioHQ/composio/tree/master/python/examples/crewai

**CrewAI Official:**
- Docs: https://docs.crewai.com/
- GitHub: https://github.com/joaomdmoura/crewAI

## Installation

```bash
# Install CrewAI with Composio
pip install crewai composio-crewai

# Or install all at once
pip install crewai composio-crewai snowflake-connector-python python-dotenv
```

## Correct Integration Pattern (Composio v3)

```python
from composio import Composio
from crewai import Agent, Task, Crew

# 1. Initialize Composio with user session
composio = Composio()
session = composio.create(user_id="incidentdna_agent")

# 2. Get tools for CrewAI
tools = session.tools(toolkits=["github", "slack"])

# 3. Create CrewAI agent with Composio tools
agent = Agent(
    role="Incident Responder",
    goal="Detect and respond to production incidents",
    backstory="You are an expert SRE...",
    tools=tools,  # Pass Composio tools here
    verbose=True
)

# 4. Create task
task = Task(
    description="Create a GitHub issue for the incident",
    agent=agent,
    expected_output="GitHub issue URL"
)

# 5. Run crew
crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()
```

## For Triggers (GitHub Push Events)

```python
from composio import Composio

composio = Composio()
session = composio.create(user_id="incidentdna_system")

# Subscribe to GitHub push events
trigger_id = session.triggers.subscribe(
    toolkit="github",
    trigger_name="GITHUB_PUSH_EVENT",
    config={
        "owner": "your-org",
        "repo": "your-repo"
    }
)

# Listen for events
for event in session.triggers.listen():
    if event.trigger_name == "GITHUB_PUSH_EVENT":
        # Trigger your CrewAI pipeline
        handle_github_push(event.payload)
```

## Authentication Setup

```bash
# 1. Login to Composio
composio login

# 2. Add GitHub integration
composio add github

# 3. Add Slack integration
composio add slack

# 4. List connected accounts
composio connected-accounts
```

## Example: CrewAI Agent with Composio Tools

```python
from composio import Composio
from crewai import Agent, Task, Crew, Process

# Initialize
composio = Composio()
session = composio.create(user_id="incident_agent")

# Get GitHub and Slack tools
tools = session.tools(toolkits=["github", "slack"])

# Create agents
detector = Agent(
    role="Incident Detector",
    goal="Detect anomalies in metrics",
    tools=tools,
    verbose=True
)

responder = Agent(
    role="Incident Responder",
    goal="Create GitHub issues and post Slack alerts",
    tools=tools,
    verbose=True
)

# Create tasks
detect_task = Task(
    description="Analyze metrics and detect anomalies",
    agent=detector,
    expected_output="Anomaly report"
)

respond_task = Task(
    description="""
    Create a GitHub issue with title: '[P1] Payment Service Error Rate Spike'
    Post a Slack alert to #incidents channel
    """,
    agent=responder,
    expected_output="GitHub issue URL and Slack message ID",
    context=[detect_task]  # Depends on detect_task
)

# Run crew
crew = Crew(
    agents=[detector, responder],
    tasks=[detect_task, respond_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print(result)
```

## Key Points

1. **Always use `composio.create(user_id)`** - This is the v3 pattern
2. **Get tools with `session.tools()`** - Pass toolkits you need
3. **Pass tools to CrewAI agents** - Use `tools=tools` parameter
4. **For triggers, use `session.triggers.subscribe()`** - Subscribe to events
5. **No manual auth setup needed** - Composio handles OAuth automatically

## Environment Variables

```bash
# .env file
COMPOSIO_API_KEY=your_composio_api_key
GITHUB_OWNER=your-github-username
GITHUB_REPO=your-repo-name
SLACK_CHANNEL=#incidents
```

## Troubleshooting

**Issue:** "No connected account found"
**Fix:** Run `composio add github` and `composio add slack`

**Issue:** "Trigger not firing"
**Fix:** Check webhook is configured in GitHub repo settings

**Issue:** "Tools not working in CrewAI"
**Fix:** Ensure you're passing `session.tools()` to the agent, not raw Composio object

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Authenticate: `composio login && composio add github && composio add slack`
3. Configure `.env` with your credentials
4. Run trigger listener: `python ingestion/trigger_listener.py`
5. Test with a GitHub push event
