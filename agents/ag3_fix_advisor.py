from crewai import Agent, Task
from utils.snowflake_llm import cortex_llm
from utils.sanitize import sanitize_sql_value
from tools.search_runbooks import SearchRunbooksTool
from tools.find_similar_incidents import FindSimilarIncidentsTool
from tools.query_snowflake import QuerySnowflakeTool


def make_fix_advisor() -> Agent:
    return Agent(
        llm=cortex_llm,
        role="Fix Advisor",
        goal=(
            "Generate ranked, specific fix commands for the identified root cause. "
            "Each fix option must include concrete steps, estimated time, risk level, "
            "and a rollback procedure."
        ),
        backstory=(
            "You are an expert SRE who has resolved thousands of production incidents. "
            "You know runbooks inside-out, and you always provide actionable, specific "
            "remediation steps — never vague suggestions. You rank fixes by speed and safety. "
            "You cross-reference runbooks and past incident fixes to provide proven solutions."
        ),
        tools=[SearchRunbooksTool(), FindSimilarIncidentsTool(), QuerySnowflakeTool()],
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )


def fix_advisor_task(agent: Agent, event: dict, investigation: dict) -> Task:
    service = sanitize_sql_value(event["service"])
    root_cause = investigation.get("root_cause", "unknown")
    recommended_action = investigation.get("recommended_action", "investigate_manually")

    return Task(
        description=f"""
Generate 3 ranked fix options for this incident.

=== INCIDENT CONTEXT ===
Service            : {service}
Root Cause         : {root_cause}
Recommended Action : {recommended_action}

=== YOUR STEPS ===
1. Search runbooks for fix steps:
   Use tool: search_runbooks
   Input: "{service} {root_cause} fix remediation steps"

2. Check how similar past incidents were fixed:
   Use tool: find_similar_incidents
   Input: "{service} {root_cause}"

=== OUTPUT FORMAT ===
Return ONLY this JSON — no explanation, no markdown:
{{
  "fix_options": [
    {{
      "rank": 1,
      "title": "short title of fix",
      "commands": ["step 1 command", "step 2 command"],
      "estimated_time": "5 minutes",
      "risk_level": "LOW|MEDIUM|HIGH",
      "rollback": "how to undo this fix"
    }},
    {{
      "rank": 2,
      "title": "...",
      "commands": ["..."],
      "estimated_time": "...",
      "risk_level": "...",
      "rollback": "..."
    }},
    {{
      "rank": 3,
      "title": "...",
      "commands": ["..."],
      "estimated_time": "...",
      "risk_level": "...",
      "rollback": "..."
    }}
  ]
}}
""",
        agent=agent,
        expected_output='Valid JSON with key: fix_options (array of 3 ranked fixes)',
    )
