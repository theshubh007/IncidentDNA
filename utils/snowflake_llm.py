"""
Snowflake Cortex LLM wrapper for CrewAI.

Uses SNOWFLAKE.CORTEX.COMPLETE with llama3.1-70b — completely free
with the hackathon Snowflake account. No external API key needed.

Model options (all free in Cortex):
  llama3.1-70b   ← default, best quality
  llama3.1-8b    ← faster, lighter
  mistral-large  ← alternative
"""

import json
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

from utils.snowflake_conn import get_connection


class SnowflakeCortexLLM(BaseChatModel):
    """
    LangChain-compatible chat model that calls Snowflake Cortex COMPLETE.
    Drop-in replacement for ChatGroq / ChatOpenAI in CrewAI agents.
    """

    model_name: str = "llama3.1-70b"
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "snowflake_cortex"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Convert LangChain messages → Snowflake messages format
        sf_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            sf_messages.append({"role": role, "content": msg.content})

        # Call SNOWFLAKE.CORTEX.COMPLETE via parameterised query (safe from injection)
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s) AS response",
                (self.model_name, json.dumps(sf_messages)),
            )
            row = cur.fetchone()
            raw = row[0] if row else ""
        finally:
            if cur:
                cur.close()

        # Parse response — COMPLETE with messages array returns JSON or plain string
        text = _extract_text(raw)

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )

    @property
    def _identifying_params(self) -> dict:
        return {"model_name": self.model_name}


def _extract_text(raw: Any) -> str:
    """Handle all response shapes from Snowflake Cortex COMPLETE."""
    if raw is None:
        return ""

    # Already a dict (Snowpark returns parsed VARIANT)
    if isinstance(raw, dict):
        choices = raw.get("choices", [])
        if choices:
            return choices[0].get("messages", str(raw))
        return str(raw)

    # String — might be plain text or JSON
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                choices = parsed.get("choices", [])
                if choices:
                    return choices[0].get("messages", raw)
            return raw
        except json.JSONDecodeError:
            return raw

    return str(raw)


# Singleton — reused across all agents to avoid re-importing
cortex_llm = SnowflakeCortexLLM(model_name="llama3.1-70b", temperature=0.0)
