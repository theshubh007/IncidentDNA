from crewai import Agent, Task
from utils.snowflake_llm import cortex_llm
from tools.query_snowflake import QuerySnowflakeTool


def make_action_agent() -> Agent:
    return Agent(
        llm=cortex_llm,
        role="Action Agent",
        goal=(
            "Execute approved incident response actions: post Slack alerts and create "
            "GitHub issues. Decide the appropriate action format based on severity, "
            "blast radius, and fix options."
        ),
        backstory=(
            "You are the communication arm of the incident team. You craft clear, "
            "actionable Slack alerts and GitHub issues that give on-call engineers "
            "everything they need to act. You include severity, blast radius, fix "
            "options, and event tracking info. You never send duplicate notifications."
        ),
        tools=[QuerySnowflakeTool()],
        verbose=True,
        allow_delegation=False,
    )


def action_task(
    agent: Agent,
    event: dict,
    detection: dict,
    investigation: dict,
    fix_options: list,
) -> Task:
    service = event["service"]
    event_id = event["event_id"]
    severity = detection.get("severity", "P3")
    blast_radius = detection.get("blast_radius", [])
    root_cause = investigation.get("root_cause", "Unknown")
    confidence = investigation.get("confidence", 0.5)

    fix_summary = ""
    for i, fix in enumerate(fix_options[:3], 1):
        title = fix.get("title", "N/A")
        risk = fix.get("risk_level", "MEDIUM")
        fix_summary += f"  {i}. {title} (risk: {risk})\n"

    blast_str = ", ".join(blast_radius) if blast_radius else "None identified"

    return Task(
        description=f"""
Compose the Slack alert and GitHub issue content for this incident.

=== INCIDENT DETAILS ===
Event ID      : {event_id}
Service       : {service}
Severity      : {severity}
Root Cause    : {root_cause}
Confidence    : {confidence}
Blast Radius  : {blast_str}
Fix Options   :
{fix_summary}

=== OUTPUT FORMAT ===
Return ONLY this JSON — no explanation, no markdown:
{{
  "slack_message": "full formatted Slack message with severity emoji, service, root cause, blast radius, and top fix options",
  "github_title": "[{severity}] {service} — short root cause summary",
  "github_body": "full markdown GitHub issue body with incident details, root cause, fix options, and resolution checklist"
}}
""",
        agent=agent,
        expected_output='Valid JSON with keys: slack_message, github_title, github_body',
    )
