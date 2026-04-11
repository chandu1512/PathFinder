"""
PathFinder v2 — RAG orchestration layer.

Exposes two high-level functions called by Flask endpoints:

  answer_chat(user_message, student_context, history, system_prompt)
      Retrieves relevant courses + careers, augments the system prompt,
      and calls Groq for a conversational response.

  generate_roadmap(prompt, system_prompt, career, major)
      Retrieves courses relevant to the target career, augments the prompt,
      and calls Groq for a structured JSON academic roadmap.
"""

from __future__ import annotations

import logging
from typing import Any

from rag import llm_client
from rag.retriever import search_careers, search_courses

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# answer_chat
# ---------------------------------------------------------------------------

def answer_chat(
    user_message: str,
    student_context: dict[str, Any],
    history: list[dict[str, str]],
    system_prompt: str,
) -> str:
    """
    RAG-augmented conversational response.

    Retrieval:
        - Top-5 courses semantically relevant to the user message
        - Top-3 careers semantically relevant to the user message

    Augmentation:
        Retrieved records are appended to the system prompt as a
        "RETRIEVED CONTEXT" block so the LLM can reference them.

    Generation:
        Calls Groq (llama-3.3-70b with auto-fallback) with the full
        conversation history.

    Args:
        user_message:    The latest user turn (used as the retrieval query).
        student_context: Pre-built context dict from app.py (unused here —
                         program data is already embedded in system_prompt).
        history:         Full conversation history including the latest user
                         message as the last entry.
        system_prompt:   Pre-built system prompt (SYSTEM_PROMPT + program context).

    Returns:
        The assistant reply string.
    """
    augmented_system = system_prompt

    try:
        top_courses = search_courses(user_message, k=5)
        top_careers = search_careers(user_message, k=3)

        rag_block = "\n\n=== RETRIEVED CONTEXT (UDel catalog — use these as examples) ===\n"

        if top_courses:
            rag_block += "Relevant courses:\n"
            for c in top_courses:
                desc = (c.get("description", "") or "")[:200].strip()
                rag_block += f"  • {c.get('code', '')} {c.get('title', '')}: {desc}\n"

        if top_careers:
            rag_block += "Relevant careers:\n"
            for career in top_careers:
                skills = ", ".join(career.get("skills", [])[:5])
                rag_block += (
                    f"  • {career.get('title', '')} ({career.get('program', '')}): "
                    f"{career.get('description', '')[:150]} Skills: {skills}\n"
                )

        augmented_system = system_prompt + rag_block

    except FileNotFoundError as exc:
        # Indices not built — degrade gracefully (no RAG context, still answers)
        logger.warning("answer_chat: FAISS indices not found, answering without RAG. %s", exc)

    return llm_client.chat_with_history(
        system_prompt=augmented_system,
        history=history,
        temperature=0.7,
        max_tokens=1024,
    )


# ---------------------------------------------------------------------------
# generate_roadmap
# ---------------------------------------------------------------------------

def generate_roadmap(
    prompt: str,
    system_prompt: str,
    career: str,
    major: str,
) -> dict[str, Any]:
    """
    Generate a structured JSON academic roadmap via RAG + Groq.

    Retrieval:
        Top-15 courses relevant to "{career} {major} courses skills".
        These are appended to the prompt as supplementary course options,
        ensuring the LLM has real UDel course data and cannot hallucinate codes.

    Generation:
        Calls Groq with JSON enforcement and parse-retry.

    Args:
        prompt:        Full roadmap prompt already built by app.py (includes
                       student profile, program courses, planning rules, and
                       the JSON schema the model must follow).
        system_prompt: The PathFinder SYSTEM_PROMPT from app.py.
        career:        Target career string (used as retrieval query component).
        major:         Student's major (used as retrieval query component).

    Returns:
        Parsed roadmap dict (semesters + outlook).

    Raises:
        ValueError: If Groq cannot produce parseable JSON after retries.
    """
    augmented_prompt = prompt

    try:
        rag_query = f"{career} {major} university courses skills"
        top_courses = search_courses(rag_query, k=5)

        if top_courses:
            rag_note = (
                "\n\nSUPPLEMENTARY COURSES FROM UDEL CATALOG "
                "(additional options — only use codes that also appear in the CORE/ELECTIVES list above):\n"
            )
            for c in top_courses:
                rag_note += f"  • {c.get('code', '')} — {c.get('title', '')}\n"
            augmented_prompt = prompt + rag_note

    except FileNotFoundError as exc:
        logger.warning(
            "generate_roadmap: FAISS indices not found, proceeding without RAG. %s", exc
        )

    return llm_client.generate_json(
        system_prompt=system_prompt,
        user_message=augmented_prompt,
        max_tokens=3500,
        retries=2,
    )
