"""
PathFinder v2 — FAISS retrieval module.

Loads the BGE embedding model and FAISS indices once at startup (lazy singleton).
Exposes search_courses() and search_careers() used by the RAG pipeline and
directly by Flask endpoints for pure-retrieval operations.

Usage:
    from rag.retriever import search_courses, search_careers

    courses = search_courses("machine learning neural networks", k=10)
    careers = search_careers("data analyst high salary", k=5)

Raises FileNotFoundError on first call if indices haven't been built yet,
with a clear message telling the user to run build_index.py.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RAG_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = os.path.join(RAG_DIR, "indices")
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# ---------------------------------------------------------------------------
# Lazy singleton state
# ---------------------------------------------------------------------------

_model: Optional[SentenceTransformer] = None
_course_index: Optional[faiss.Index] = None
_career_index: Optional[faiss.Index] = None
_courses_meta: Optional[list[dict[str, Any]]] = None
_careers_meta: Optional[list[dict[str, Any]]] = None


def _check_index_files() -> None:
    """Raise a clear FileNotFoundError if any index file is missing."""
    required = (
        "courses.faiss",
        "careers.faiss",
        "courses_meta.json",
        "careers_meta.json",
    )
    missing = [f for f in required if not os.path.exists(os.path.join(INDEX_DIR, f))]
    if missing:
        raise FileNotFoundError(
            f"FAISS index files missing: {missing}\n"
            "Build the indices first by running:\n"
            "    python -m rag.build_index\n"
            "from the project root, then commit rag/indices/ to the repo."
        )


def _ensure_loaded() -> None:
    """Load model and indices on first call; no-op on subsequent calls."""
    global _model, _course_index, _career_index, _courses_meta, _careers_meta

    if _model is not None:
        return  # already loaded

    _check_index_files()

    t0 = time.time()
    logger.info("Retriever: loading BGE embedding model '%s'...", MODEL_NAME)
    _model = SentenceTransformer(MODEL_NAME)
    logger.info("Retriever: model loaded in %.1fs", time.time() - t0)

    t1 = time.time()
    logger.info("Retriever: loading FAISS indices...")
    _course_index = faiss.read_index(os.path.join(INDEX_DIR, "courses.faiss"))
    _career_index = faiss.read_index(os.path.join(INDEX_DIR, "careers.faiss"))

    with open(os.path.join(INDEX_DIR, "courses_meta.json")) as f:
        _courses_meta = json.load(f)
    with open(os.path.join(INDEX_DIR, "careers_meta.json")) as f:
        _careers_meta = json.load(f)

    logger.info(
        "Retriever: indices loaded in %.1fs — courses: %d, careers: %d",
        time.time() - t1,
        _course_index.ntotal,
        _career_index.ntotal,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _embed(query: str) -> np.ndarray:
    """Embed a single query into a normalized float32 row vector (1, dim)."""
    vec = _model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vec.astype(np.float32)


def _course_level_from_code(code: str) -> str:
    """Infer undergrad/grad from the numeric part of a course code."""
    m = re.search(r"(\d{3,4})", code)
    if m:
        return "grad" if int(m.group(1)) >= 600 else "undergrad"
    return "undergrad"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_courses(
    query: str,
    k: int = 10,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Semantic search over the UDel course catalog using FAISS.

    Args:
        query:   Natural language query (e.g. "machine learning algorithms").
        k:       Number of results to return.
        filters: Optional dict with any combination of:
                   - "level" (str): "undergrad" | "grad"
                   - "preferred_depts" (list[str]): e.g. ["CISC", "MATH"]
                     Only courses whose dept is in this list are returned.

    Returns:
        List of course dicts (same fields as all_courses.json) with an extra
        "score" field (float, higher = more similar, max ~1.0).

    Raises:
        FileNotFoundError: if FAISS indices haven't been built yet.
    """
    _ensure_loaded()

    t0 = time.time()

    # Over-fetch to leave room for post-hoc filtering
    has_filters = bool(filters)
    fetch_k = (
        min(max(k * 60, 600), _course_index.ntotal)
        if has_filters
        else min(k * 4, _course_index.ntotal)
    )

    scores, indices = _course_index.search(_embed(query), fetch_k)

    results: list[dict[str, Any]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        course = dict(_courses_meta[idx])
        course["score"] = float(score)

        if filters:
            # Level filter
            level_filter = filters.get("level", "")
            if level_filter:
                record_level = course.get("level") or _course_level_from_code(
                    course.get("code", "")
                )
                if record_level != level_filter:
                    continue

            # Department whitelist filter
            preferred_depts: list[str] = filters.get("preferred_depts", [])
            if preferred_depts:
                if course.get("dept", "") not in preferred_depts:
                    continue

        results.append(course)
        if len(results) >= k:
            break

    elapsed_ms = (time.time() - t0) * 1000
    logger.info(
        "search_courses(%r, k=%d, filters=%s) → %d results in %.0fms",
        query[:60],
        k,
        filters,
        len(results),
        elapsed_ms,
    )
    return results


def search_careers(
    query: str,
    k: int = 10,
) -> list[dict[str, Any]]:
    """
    Semantic search over career roles using FAISS.

    Args:
        query: Natural language query (e.g. "high paying data jobs").
        k:     Number of results to return. Note: the careers index may contain
               duplicate job titles from different programs — callers should
               deduplicate by title if needed.

    Returns:
        List of career dicts (title, description, skills, salary_min,
        salary_max, demand, program) with an extra "score" field.

    Raises:
        FileNotFoundError: if FAISS indices haven't been built yet.
    """
    _ensure_loaded()

    t0 = time.time()
    fetch_k = min(k * 4, _career_index.ntotal)
    scores, indices = _career_index.search(_embed(query), fetch_k)

    results: list[dict[str, Any]] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        career = dict(_careers_meta[idx])
        career["score"] = float(score)
        results.append(career)
        if len(results) >= k:
            break

    elapsed_ms = (time.time() - t0) * 1000
    logger.info(
        "search_careers(%r, k=%d) → %d results in %.0fms",
        query[:60],
        k,
        len(results),
        elapsed_ms,
    )
    return results


# ---------------------------------------------------------------------------
# OO interface (for code that prefers class-based access)
# ---------------------------------------------------------------------------

class Retriever:
    """
    Thin OO wrapper around the module-level search functions.
    All instances share the same lazy-loaded singleton state.
    """

    def search_courses(
        self,
        query: str,
        k: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        return search_courses(query, k=k, filters=filters)

    def search_careers(self, query: str, k: int = 10) -> list[dict[str, Any]]:
        return search_careers(query, k=k)
