#!/usr/bin/env python3
"""
PathFinder v2 — One-time FAISS index builder.

Run from the project root BEFORE first deploy:
    python -m rag.build_index

Produces:
    rag/indices/courses.faiss      — 8k+ UDel course vectors
    rag/indices/careers.faiss      — 920+ career role vectors
    rag/indices/courses_meta.json  — full course records (list, index-aligned)
    rag/indices/careers_meta.json  — full career records (list, index-aligned)

Idempotent: safe to re-run. Existing index files are overwritten.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_DIR = os.path.join(RAG_DIR, "indices")

MODEL_NAME = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 256  # CPU-friendly batch size


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_courses() -> list[dict[str, Any]]:
    path = os.path.join(BASE_DIR, "all_courses.json")
    with open(path) as f:
        courses = json.load(f)
    print(f"  Courses loaded: {len(courses):,}")
    return courses


def load_careers() -> list[dict[str, Any]]:
    """Flatten all_jobs.json (program -> [jobs]) into a flat list with program field."""
    path = os.path.join(BASE_DIR, "all_jobs.json")
    with open(path) as f:
        jobs_by_program: dict[str, list[dict]] = json.load(f)

    careers: list[dict[str, Any]] = []
    for program, jobs in jobs_by_program.items():
        for job in jobs:
            careers.append(
                {
                    "title": job.get("title", ""),
                    "description": job.get("description", ""),
                    "skills": job.get("skills", []),
                    "salary_min": job.get("salary_min", 0),
                    "salary_max": job.get("salary_max", 0),
                    "demand": job.get("demand", "Medium"),
                    "program": program,
                }
            )
    print(f"  Careers loaded: {len(careers):,} (across {len(jobs_by_program)} programs)")
    return careers


# ---------------------------------------------------------------------------
# Embedding text construction
# ---------------------------------------------------------------------------

def make_course_text(course: dict[str, Any]) -> str:
    """
    Build a rich embedding string for a course record.
    Format: "{code} {title}. {description[:500]} Level: {level}. Department: {dept}"
    """
    code = course.get("code", "")
    title = course.get("title", "")
    description = (course.get("description", "") or "")[:500]
    level = course.get("level", "undergrad")
    dept = course.get("dept", "")
    return f"{code} {title}. {description} Level: {level}. Department: {dept}"


def make_career_text(career: dict[str, Any]) -> str:
    """
    Build a rich embedding string for a career record.
    Format: "{title}. {description} Skills: {skills}. Program: {program}"
    """
    title = career.get("title", "")
    description = career.get("description", "")
    skills = ", ".join(career.get("skills", []))
    program = career.get("program", "")
    return f"{title}. {description} Skills: {skills}. Program: {program}"


# ---------------------------------------------------------------------------
# Embedding + index construction
# ---------------------------------------------------------------------------

def embed_texts(
    model: SentenceTransformer,
    texts: list[str],
    label: str,
) -> np.ndarray:
    """Embed texts in batches. Returns normalized float32 array of shape (N, dim)."""
    print(f"  Embedding {len(texts):,} {label}...")
    t0 = time.time()
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,   # enables cosine sim via inner product
        convert_to_numpy=True,
    )
    elapsed = time.time() - t0
    arr = embeddings.astype(np.float32)
    print(f"  Done in {elapsed:.1f}s — shape {arr.shape}")
    return arr


def build_flat_ip_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Build an IndexFlatIP (exact cosine similarity via normalized inner product)."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def save(
    index: faiss.Index,
    meta: list[dict[str, Any]],
    name: str,
) -> None:
    """Save FAISS index + metadata JSON to rag/indices/."""
    os.makedirs(INDEX_DIR, exist_ok=True)

    faiss_path = os.path.join(INDEX_DIR, f"{name}.faiss")
    meta_path = os.path.join(INDEX_DIR, f"{name}_meta.json")

    faiss.write_index(index, faiss_path)
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    faiss_mb = os.path.getsize(faiss_path) / 1024 / 1024
    print(f"  Saved {faiss_path} ({faiss_mb:.1f} MB) + {meta_path} ({len(meta):,} records)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("PathFinder v2 — FAISS Index Builder")
    print("=" * 60)

    print("\nLoading data...")
    courses = load_courses()
    careers = load_careers()

    print(f"\nLoading embedding model: {MODEL_NAME}")
    t0 = time.time()
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    print(f"  Model ready in {time.time()-t0:.1f}s — embedding dim: {dim}")

    # ── Courses index ──────────────────────────────────────────────────────
    print("\n[1/2] Building courses index...")
    course_texts = [make_course_text(c) for c in courses]
    course_embeddings = embed_texts(model, course_texts, "courses")
    course_index = build_flat_ip_index(course_embeddings)
    save(course_index, courses, "courses")
    print(f"  courses.faiss: {course_index.ntotal:,} vectors")

    # ── Careers index ──────────────────────────────────────────────────────
    print("\n[2/2] Building careers index...")
    career_texts = [make_career_text(c) for c in careers]
    career_embeddings = embed_texts(model, career_texts, "careers")
    career_index = build_flat_ip_index(career_embeddings)
    save(career_index, careers, "careers")
    print(f"  careers.faiss: {career_index.ntotal:,} vectors")

    print("\n" + "=" * 60)
    print("Build complete!")
    print(f"  Courses index: {course_index.ntotal:,} vectors @ dim={dim}")
    print(f"  Careers index: {career_index.ntotal:,} vectors @ dim={dim}")
    print()
    print("Next steps:")
    print("  git add rag/indices/ && git commit -m 'Add FAISS indices'")
    print("  git push  # Railway will auto-deploy")
    print("=" * 60)


if __name__ == "__main__":
    main()
