"""
PathFinder v2 — Groq LLM client.

Two-model split:
  CHAT_MODEL    — used by chat() and chat_with_history()  (conversational)
  ROADMAP_MODEL — used by generate_json()                 (structured output)
  FALLBACK_MODEL — used by all three on any error

All three models are configurable via environment variables.
Per-request logging: model, latency, token counts.

Shared _client singleton is created at import time using GROQ_API_KEY from env.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

from groq import Groq

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration — override via env vars
# ---------------------------------------------------------------------------

ROADMAP_MODEL = os.getenv("ROADMAP_MODEL", "openai/gpt-oss-120b")
CHAT_MODEL    = os.getenv("CHAT_MODEL",    "qwen/qwen3-32b")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama-3.1-8b-instant")

# ---------------------------------------------------------------------------
# Shared client — created once at module import
# ---------------------------------------------------------------------------

_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Single Groq API call. Logs latency and token usage.
    Returns the content string from the first choice.
    """
    t0 = time.time()
    response = _client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    elapsed_ms = (time.time() - t0) * 1000
    usage = response.usage
    logger.info(
        "Groq [%s] %.0fms | prompt=%d completion=%d tokens",
        model,
        elapsed_ms,
        usage.prompt_tokens,
        usage.completion_tokens,
    )
    return response.choices[0].message.content


def _call_with_fallback(
    messages: list[dict[str, str]],
    primary_model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Try primary_model first. On any exception, retry with FALLBACK_MODEL.
    The fallback exception is allowed to propagate if it also fails.
    """
    try:
        return _call(messages, primary_model, temperature, max_tokens)
    except Exception as primary_exc:
        logger.warning(
            "Model %s failed, switching to fallback %s: %s",
            primary_model,
            FALLBACK_MODEL,
            primary_exc,
        )
        return _call(messages, FALLBACK_MODEL, temperature, max_tokens)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from a response string."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def _extract_json_object(text: str) -> str:
    """Extract the first top-level JSON object from a string."""
    m = re.search(r"\{[\s\S]*\}", text)
    return m.group(0) if m else text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """
    Single-turn chat. Uses CHAT_MODEL with auto-fallback to FALLBACK_MODEL.

    Args:
        system_prompt: System instructions for the assistant.
        user_message:  The user's input.
        temperature:   Sampling temperature (0 = deterministic, 1 = creative).
        max_tokens:    Maximum tokens in the response.

    Returns:
        The assistant's reply as a plain string.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    return _call_with_fallback(messages, CHAT_MODEL, temperature, max_tokens)


def chat_with_history(
    system_prompt: str,
    history: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """
    Multi-turn chat with conversation history. Uses CHAT_MODEL with auto-fallback.

    Args:
        system_prompt: System instructions prepended to the conversation.
        history:       List of {"role": "user"|"assistant", "content": "..."} dicts.
                       The last message should be from the user.
        temperature:   Sampling temperature.
        max_tokens:    Maximum tokens in the response.

    Returns:
        The assistant's reply as a plain string.
    """
    messages = [{"role": "system", "content": system_prompt}] + history
    return _call_with_fallback(messages, CHAT_MODEL, temperature, max_tokens)


def generate_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
    retries: int = 2,
) -> dict[str, Any]:
    """
    Generate a JSON response and parse it. Uses ROADMAP_MODEL with auto-fallback.

    Appends a strict "respond only with JSON" instruction to the system prompt.
    On parse failure, retries — first with FALLBACK_MODEL, then again if retries > 1.
    Strips markdown code fences and extracts the first JSON object if the model
    adds surrounding text.

    Args:
        system_prompt: Base system instructions.
        user_message:  Prompt describing what JSON to produce.
        max_tokens:    Maximum tokens in the response.
        retries:       Number of additional attempts after the first (default 2).

    Returns:
        Parsed dict.

    Raises:
        ValueError: If all attempts fail to produce valid JSON.
    """
    enforced_system = (
        system_prompt
        + "\n\nCRITICAL OUTPUT RULE: Respond ONLY with a valid JSON object. "
        "No markdown, no code fences, no explanation before or after the JSON."
    )
    messages = [
        {"role": "system", "content": enforced_system},
        {"role": "user", "content": user_message},
    ]

    # Attempt order: ROADMAP_MODEL first, then FALLBACK_MODEL for remaining retries
    attempt_models = ([ROADMAP_MODEL] + [FALLBACK_MODEL] * retries)[: retries + 1]
    last_exc: Optional[Exception] = None

    for attempt, model in enumerate(attempt_models):
        try:
            raw = _call(messages, model, temperature=0.2, max_tokens=max_tokens)
            cleaned = _strip_code_fences(raw)
            cleaned = _extract_json_object(cleaned)
            return json.loads(cleaned)
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "generate_json attempt %d/%d failed (model=%s): %s",
                attempt + 1,
                len(attempt_models),
                model,
                exc,
            )
            continue

    raise ValueError(
        f"generate_json failed after {len(attempt_models)} attempts: {last_exc}"
    )
