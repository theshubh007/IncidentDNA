from crewai import Agent, Task
from langchain_groq import ChatGroq
from tools.query_snowflake import QuerySnowflakeTool

_llm = ChatGroq(model="llama3-70b-8192", temperature=0)


def make_detector() -> Agent:
    return Agent(
        llm=_llm,
        role="Incident Detector",
        goal=(
            "Classify the severity of a production anomaly (P1/P2/P3) "
            "and identify which downstream services are in the blast radius."
        ),
        backstory=(
            "You are a battle-hardened SRE with 10 years of on-call experience. "
            "You are fast, precise, and never over-escalate. You use z-scores from "
            "ANALYTICS.METRIC_DEVIATIONS to confirm severity, and RAW.SERVICE_DEPENDENCIES "
            "to map the blast radius. You output clean, valid JSON — nothing else."
        ),
        tools=[QuerySnowflakeTool()],
        verbose=True,
        allow_delegation=False,
    )


def detector_task(agent: Agent, event: dict) -> Task:
    service = event["service"]
    return Task(
        description=f"""
Analyze this production anomaly and classify it precisely.

=== INCIDENT INPUT ===
Event ID       : {event['event_id']}
Service        : {service}
Anomaly Type   : {event['anomaly_type']}
Severity Signal: {event['severity']}
Details        : {event.get('details', {})}

=== YOUR STEPS ===
1. Run this query to get the blast radius:
   SELECT depends_on FROM RAW.SERVICE_DEPENDENCIES WHERE service = '{service}'

2. Run this query to confirm severity from live metrics:
   SELECT metric_name, current_value, baseline_avg, z_score, severity
   FROM ANALYTICS.METRIC_DEVIATIONS
   WHERE service = '{service}'
   ORDER BY z_score DESC
   LIMIT 10

3. Map z_score to severity:
   z_score > 3  → P1 (critical, page immediately)
   z_score > 2  → P2 (high, act within 30 min)
   z_score <= 2 → P3 (medium, monitor)

=== OUTPUT FORMAT ===
Return ONLY this JSON — no explanation, no markdown:
{{"severity": "P1|P2|P3", "blast_radius": ["service1", "service2"], "classification": "one-line description of what is happening"}}
""",
        agent=agent,
        expected_output='Valid JSON with keys: severity, blast_radius, classification',
    )
