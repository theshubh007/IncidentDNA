from crewai import Agent, Task
from utils.snowflake_llm import cortex_llm
from utils.sanitize import sanitize_sql_value
from tools.search_runbooks import SearchRunbooksTool
from tools.find_similar_incidents import FindSimilarIncidentsTool
from tools.query_snowflake import QuerySnowflakeTool


def make_investigator() -> Agent:
    return Agent(
        llm=cortex_llm,
        role="Root Cause Investigator",
        goal=(
            "Determine the definitive root cause of the incident using 3 mandatory evidence sources: "
            "(1) Runbook knowledge base via Cortex Search, "
            "(2) Past incident history via semantic similarity, "
            "(3) Live metric deviation data from Snowflake. "
            "Output a confidence score 0.0–1.0 and a concrete recommended action."
        ),
        backstory=(
            "You are a forensic incident engineer. You never guess — you evidence-chain. "
            "You MUST use all 3 tools before forming a conclusion. "
            "If runbook and past-incident evidence is weak (confidence < 0.6), "
            "you reason from first principles using the raw metric data. "
            "You are the most important agent in the pipeline — precision matters."
        ),
        tools=[SearchRunbooksTool(), FindSimilarIncidentsTool(), QuerySnowflakeTool()],
        verbose=True,
        allow_delegation=False,
    )


def investigator_task(agent: Agent, event: dict, detection: dict) -> Task:
    service = sanitize_sql_value(event["service"])
    anomaly = event["anomaly_type"]
    severity = detection.get("severity", event["severity"])
    classification = detection.get("classification", anomaly)
    blast_radius = detection.get("blast_radius", [])
    
    # Support debate loop: include validator feedback if present
    validator_objections = event.get("validator_objections", [])
    validator_notes = event.get("validator_notes", "")
    
    feedback_section = ""
    if validator_objections or validator_notes:
        objections_str = "\n".join(f"  - {obj}" for obj in validator_objections) if validator_objections else "  (none)"
        feedback_section = f"""

=== VALIDATOR FEEDBACK (address these concerns) ===
Objections:
{objections_str}
Notes: {validator_notes or '(none)'}

You MUST address each objection in your revised analysis. If the validator raised
a concern about alternative causes, investigate them. If evidence was weak, find
stronger evidence. Your confidence should reflect how well you addressed these.
"""

    return Task(
        description=f"""
Investigate the root cause of this confirmed incident. Use ALL 3 tools.

=== INCIDENT CONTEXT ===
Service        : {service}
Severity       : {severity}
Classification : {classification}
Blast Radius   : {blast_radius}
Anomaly Type   : {anomaly}{feedback_section}

=== MANDATORY STEPS — complete ALL 3 ===

STEP 1 — Search runbooks:
  Use tool: search_runbooks
  Input: "{service} {anomaly} {classification} symptoms fix"

STEP 2 — Find similar past incidents:
  Use tool: find_similar_incidents
  Input: "{service} {classification} after deploy"

STEP 3 — Query live metric deviations:
  Use tool: query_snowflake
  SQL: SELECT metric_name, current_value, baseline_avg, z_score FROM ANALYTICS.METRIC_DEVIATIONS WHERE service = '{service}' ORDER BY z_score DESC LIMIT 10

=== SYNTHESIS RULES ===
- If runbook + past incident both point to the same cause → confidence >= 0.85
- If only one source matches → confidence 0.60–0.75
- If neither matches → reason from raw metrics (first principles) → confidence 0.50–0.65
- recommended_action must be one of: rollback | fix_config | restart | scale_up | escalate | investigate_manually

=== OUTPUT FORMAT ===
Return ONLY this JSON — no explanation, no markdown:
{{"root_cause": "detailed description of what caused this", "confidence": 0.0-1.0, "evidence_sources": ["runbook", "past_incident", "metrics"], "recommended_action": "one of the valid actions above"}}
""",
        agent=agent,
        expected_output='Valid JSON with keys: root_cause, confidence, evidence_sources, recommended_action',
    )
