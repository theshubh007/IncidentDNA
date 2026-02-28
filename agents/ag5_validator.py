from crewai import Agent, Task
from tools.query_snowflake import QuerySnowflakeTool


def make_validator() -> Agent:
    return Agent(
        role="Adversarial Validator",
        goal=(
            "Stress-test the proposed root cause by running 4 adversarial checks. "
            "APPROVE only if the hypothesis survives all 4 checks. "
            "DEBATE if any check reveals a serious flaw."
        ),
        backstory=(
            "You are the most skeptical engineer on the team. You have seen wrong diagnoses "
            "trigger rollbacks that made things worse, wasting 2+ hours. "
            "Your job is NOT to agree — it is to find holes. "
            "You run 4 checks: alternative causes, evidence quality, fix safety, and simplicity. "
            "You are the last line of defense before actions are taken on production systems. "
            "You output clean JSON with your verdict and specific objections."
        ),
        tools=[QuerySnowflakeTool()],
        verbose=True,
        allow_delegation=False,
    )


def validator_task(agent: Agent, investigation: dict, event: dict) -> Task:
    service = event["service"]
    root_cause = investigation.get("root_cause", "unknown")
    confidence = investigation.get("confidence", 0.5)
    evidence = investigation.get("evidence_sources", [])
    action = investigation.get("recommended_action", "unknown")

    return Task(
        description=f"""
CHALLENGE this proposed root cause. Be adversarial. Do NOT accept it unless it passes all 4 checks.

=== PROPOSED DIAGNOSIS ===
Root cause        : {root_cause}
Confidence        : {confidence}
Evidence sources  : {evidence}
Recommended action: {action}
Service           : {service}

=== 4 ADVERSARIAL CHECKS — run all of them ===

CHECK 1 — Alternative causes:
  What ELSE could produce these exact metrics for {service}?
  Query if needed: SELECT metric_name, current_value, z_score FROM ANALYTICS.METRIC_DEVIATIONS WHERE service = '{service}' LIMIT 10
  Are there other equally plausible explanations?

CHECK 2 — Evidence quality:
  Is the evidence direct or circumstantial?
  Does the runbook/past-incident actually describe THIS exact pattern, or is it loosely similar?
  Would you stake production on this evidence?

CHECK 3 — Fix safety:
  Could "{action}" make the situation WORSE?
  What is the rollback plan if it fails?
  Is there a risk of cascading failures?

CHECK 4 — Simplicity (Occam's Razor):
  Is there a simpler explanation that fits the data equally well?
  Are we over-engineering the diagnosis?

=== DECISION RULES ===
APPROVE if:
  - No strong alternative causes found
  - Evidence is direct, not circumstantial
  - Fix is safe with low rollback risk
  - No simpler explanation fits better
  - confidence >= 0.7

DEBATE if ANY of:
  - A strong alternative cause exists
  - Evidence is weak or circumstantial
  - Fix could worsen the incident
  - A simpler explanation fits better
  - confidence < 0.7

=== OUTPUT FORMAT ===
Return ONLY this JSON — no explanation, no markdown:
{{"verdict": "APPROVED|DEBATE", "confidence_adjustment": <float between -0.3 and +0.1>, "objections": ["specific objection 1", "specific objection 2"], "notes": "one-sentence summary of your decision"}}
""",
        agent=agent,
        expected_output='Valid JSON with keys: verdict, confidence_adjustment, objections, notes',
    )
