"""
LLM provider for CrewAI agents.

Priority order (auto-selected based on available credentials):
  1. Snowflake Cortex  -- if SNOWFLAKE_CORTEX_ENABLED=true in .env
  2. Gemini            -- if GEMINI_API_KEY set (Google AI Studio)
  3. Groq              -- if GROQ_API_KEY set (free at console.groq.com)
  4. OpenAI            -- if OPENAI_API_KEY set

Default: Gemini 2.5 Flash (free tier).
Cortex COMPLETE is not available on this account type.
Cortex SEARCH and SIMILARITY still work for tools.
"""

import os
import json
from typing import Any, Iterator

import litellm
from litellm import CustomLLM, ModelResponse
from litellm.types.utils import Choices, Message, Usage
from crewai import LLM

from utils.snowflake_conn import get_connection


# ── Snowflake Cortex COMPLETE provider (use if account supports it) ───────────

def _extract_text(raw: Any) -> str:
    """Handle all response shapes from CORTEX.COMPLETE."""
    if raw is None:
        return ""
    if isinstance(raw, dict):
        choices = raw.get("choices", [])
        if choices:
            return choices[0].get("messages", choices[0].get("message", str(raw)))
        return str(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                choices = parsed.get("choices", [])
                if choices:
                    return choices[0].get("messages", choices[0].get("message", raw))
            return raw
        except json.JSONDecodeError:
            return raw
    return str(raw)


class _SnowflakeCortexHandler(CustomLLM):
    """LiteLLM custom handler -> SNOWFLAKE.CORTEX.COMPLETE."""

    def completion(self, model: str, messages: list, **kwargs: Any) -> ModelResponse:
        model_name = model.split("/")[-1] if "/" in model else "llama3.1-70b"
        conn = get_connection()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s) AS response",
                (model_name, json.dumps(messages)),
            )
            row = cur.fetchone()
            raw = row[0] if row else ""
        finally:
            if cur:
                cur.close()
            conn.close()
        text = _extract_text(raw)
        return ModelResponse(
            choices=[Choices(message=Message(content=text, role="assistant"), finish_reason="stop", index=0)],
            model=model,
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

    def streaming(self, model: str, messages: list, **kwargs: Any) -> Iterator:
        yield self.completion(model=model, messages=messages, **kwargs)


_cortex_handler = _SnowflakeCortexHandler()
litellm.custom_provider_map = [
    {"provider": "snowflake-cortex", "custom_handler": _cortex_handler}
]
litellm.set_verbose = False
litellm.num_retries = 6          # auto-retry with backoff on 429 rate limits


# ── Auto-select LLM ───────────────────────────────────────────────────────────

def _make_llm() -> LLM:
    """Pick the best available LLM in priority order."""

    # Option 1: Snowflake Cortex (only if explicitly enabled)
    if os.getenv("SNOWFLAKE_CORTEX_ENABLED", "").lower() == "true":
        print("[LLM] Using Snowflake Cortex llama3.1-70b")
        return LLM(model="snowflake-cortex/llama3.1-70b", temperature=0.0)

    # Option 2: Gemini (Google AI Studio — free tier)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        print("[LLM] Using Gemini 2.5 Flash")
        return LLM(
            model="gemini/gemini-2.5-flash",
            api_key=gemini_key,
            temperature=0.0,
        )

    # Option 3: Groq (free -- get key at console.groq.com)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        print("[LLM] Using Groq llama-3.3-70b-versatile (12k TPM — phase sleeps active)")
        return LLM(
            model="groq/llama-3.3-70b-versatile",
            api_key=groq_key,
            temperature=0.0,
            max_retries=6,
        )

    # Option 4: OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("[LLM] Using OpenAI gpt-4o-mini")
        return LLM(model="gpt-4o-mini", api_key=openai_key, temperature=0.0)

    raise EnvironmentError(
        "\n\n[LLM] No LLM configured!\n"
        "  Option A (recommended): Add GEMINI_API_KEY=... to your .env\n"
        "                          Get key free at https://aistudio.google.com/apikey\n"
        "  Option B: Add GROQ_API_KEY=... to your .env (https://console.groq.com)\n"
        "  Option C: Add OPENAI_API_KEY=... to your .env\n"
        "  Option D: Set SNOWFLAKE_CORTEX_ENABLED=true if your account supports it\n"
    )


# Singleton -- all agents import this
cortex_llm = _make_llm()
