#!/usr/bin/env python3
"""
PathFinder v2 — Sanity-check test script.

Runs 3 sample queries end-to-end and prints outputs so you can verify
the RAG stack is working before deploying to Railway.

Usage (from project root):
    python -m rag.test_pipeline

Prerequisites:
    1. GROQ_API_KEY set in environment (or .env file)
    2. FAISS indices built:  python -m rag.build_index
"""

from __future__ import annotations

import json
import os
import sys
import time

# Load .env if present (same logic as app.py)
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

# Validate environment
if not os.environ.get("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY not set. Add it to your .env file or export it.")
    sys.exit(1)

print("=" * 65)
print("PathFinder v2 — Pipeline Sanity Check")
print("=" * 65)

# ── Test 1: Career search ───────────────────────────────────────────────────

print("\n[TEST 1] Career search: 'high paying tech jobs'")
print("-" * 50)
t0 = time.time()
from rag.retriever import search_careers
results = search_careers("high paying tech jobs", k=5)
elapsed = (time.time() - t0) * 1000
print(f"  Retrieved {len(results)} careers in {elapsed:.0f}ms")
for r in results:
    salary = (
        f"${r.get('salary_min', 0)//1000}k-${r.get('salary_max', 0)//1000}k"
        if r.get("salary_min")
        else "varies"
    )
    print(f"  • {r['title']} ({r['program']}) — {r['demand']} demand — {salary}")
assert len(results) > 0, "search_careers returned no results!"
print("  ✓ PASS")

# ── Test 2: Course search with filters ─────────────────────────────────────

print("\n[TEST 2] Course search: 'machine learning neural networks' (CISC/MATH, grad)")
print("-" * 50)
t0 = time.time()
from rag.retriever import search_courses
course_results = search_courses(
    "machine learning neural networks",
    k=5,
    filters={"level": "grad", "preferred_depts": ["CISC", "MATH", "CPEG"]},
)
elapsed = (time.time() - t0) * 1000
print(f"  Retrieved {len(course_results)} grad courses in {elapsed:.0f}ms")
for c in course_results:
    print(f"  • {c.get('code', '')} — {c.get('title', '')} (score={c['score']:.3f})")
assert len(course_results) > 0, "search_courses returned no results!"
print("  ✓ PASS")

# ── Test 3: Roadmap generation ─────────────────────────────────────────────

print("\n[TEST 3] Roadmap generation: CS Junior → Software Engineer")
print("-" * 50)

# Minimal prompt mirroring the app.py roadmap endpoint
roadmap_prompt = """You are a professional academic advisor at the University of Delaware.
Build a 2-semester course plan for ONE specific academic year of this student's program.

STUDENT PROFILE:
- Major: Computer Science
- Career Goal: Software Engineer
- Current Standing: Junior
- Already Completed (do NOT repeat these): CISC 101, CISC 106, CISC 108, CISC 181, CISC 210, CISC 220

PLANNING RULES:
1. Output EXACTLY 2 semesters — Fall and Spring of Year 3 (Junior) ONLY.
2. Each semester: 3–5 courses (12–16 credits).
3. Focus on 300–400 level (intermediate/advanced) courses.
4. For each course, write exactly one sentence explaining how it builds skills for Software Engineer.

Return ONLY valid JSON, no markdown, no explanation:
{
  "semesters": [
    {
      "label": "Junior – Fall",
      "season": "Fall",
      "year": 3,
      "courses": [
        {"code": "DEPT 101", "name": "Full Course Name", "credits": 3, "why": "Specific reason."}
      ]
    }
  ],
  "outlook": "2-3 sentences on career prospects for Software Engineer graduates from UDel."
}"""

SYSTEM_PROMPT_STUB = (
    "You are PathFinder AI — an academic and career advisor exclusively for "
    "University of Delaware (UDel) students. "
    "Use ONLY real UDel course codes — never invent course numbers."
)

t0 = time.time()
from rag import pipeline as rag_pipeline
try:
    roadmap = rag_pipeline.generate_roadmap(
        prompt=roadmap_prompt,
        system_prompt=SYSTEM_PROMPT_STUB,
        career="Software Engineer",
        major="Computer Science",
    )
    elapsed = (time.time() - t0) * 1000
    print(f"  Roadmap generated in {elapsed:.0f}ms")
    semesters = roadmap.get("semesters", [])
    print(f"  Semesters returned: {len(semesters)}")
    for sem in semesters:
        label = sem.get("label", sem.get("season", "?"))
        courses = sem.get("courses", [])
        print(f"  {label}: {len(courses)} courses")
        for c in courses[:3]:
            print(f"    – {c.get('code', '?')} {c.get('name', '?')}")
    print(f"  Outlook: {roadmap.get('outlook', '')[:120]}...")
    assert semesters, "No semesters in roadmap!"
    print("  ✓ PASS")
except ValueError as e:
    print(f"  ✗ FAIL (JSON parse error): {e}")
    sys.exit(1)

# ── Test 4: Chat ───────────────────────────────────────────────────────────

print("\n[TEST 4] Chat: 'What grad courses should I take for machine learning?'")
print("-" * 50)

history = [
    {"role": "user", "content": "I'm doing my masters in Computer Science."},
    {"role": "assistant", "content": "Great! I can help with your CS MS program at UDel."},
    {"role": "user", "content": "What grad courses should I take for machine learning?"},
]

t0 = time.time()
reply = rag_pipeline.answer_chat(
    user_message="What grad courses should I take for machine learning?",
    student_context={},
    history=history,
    system_prompt=SYSTEM_PROMPT_STUB,
)
elapsed = (time.time() - t0) * 1000
print(f"  Chat reply in {elapsed:.0f}ms")
print(f"  Reply ({len(reply)} chars):")
print(f"  {reply[:400]}{'...' if len(reply) > 400 else ''}")
assert len(reply) > 20, "Chat reply too short!"
print("  ✓ PASS")

# ── Summary ────────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("All tests passed! PathFinder v2 RAG stack is operational.")
print("=" * 65)
