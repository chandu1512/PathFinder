from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_compress import Compress
import json
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Load .env file if present (local development)
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())
except FileNotFoundError:
    pass

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
Compress(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# In-memory cache for AI course matches (persists across requests)
AI_MATCH_CACHE = {}

# ── Load data at startup ──
with open(os.path.join(BASE_DIR, 'all_jobs.json'), 'r') as f:
    JOBS_DATA = json.load(f)
with open(os.path.join(BASE_DIR, 'all_courses.json'), 'r') as f:
    COURSES_DATA = json.load(f)

# Load program requirements (scraped from UDel catalog)
PROGRAM_REQUIREMENTS = []
_prog_req_path = os.path.join(BASE_DIR, 'program_requirements.json')
if os.path.exists(_prog_req_path):
    with open(_prog_req_path, 'r') as f:
        _req_data = json.load(f)
        for level, progs in _req_data.items():
            for p in progs:
                p['level_type'] = level
                PROGRAM_REQUIREMENTS.append(p)
    print(f"  Program requirements loaded: {len(PROGRAM_REQUIREMENTS)}")

# Load real program course lists scraped from UDel Major Finder
PROGRAM_COURSES = {}
_prog_courses_path = os.path.join(BASE_DIR, 'program_courses.json')
if os.path.exists(_prog_courses_path):
    with open(_prog_courses_path, 'r') as f:
        PROGRAM_COURSES = json.load(f)
    print(f"  Program courses loaded: {len(PROGRAM_COURSES)} programs")

# Build core-courses lookup per program (used for ⭐ Core badge)
# Filled after PROG_DEPTS definition (both dicts populated together)
PROG_CORE_COURSES = {}
PROG_ELECTIVE_COURSES = {}

# Title → code lookup for AI-match endpoint
COURSE_TITLE_TO_CODE = {c.get('title', ''): c.get('code', '') for c in COURSES_DATA}

# Code → title lookup for injecting real course names into AI context
COURSE_CODE_TO_TITLE = {c.get('code', ''): c.get('title', '') for c in COURSES_DATA if c.get('code')}


def extract_core_elective_codes(program):
    """
    Parse a program's requirements_text to split courses into core vs elective.

    Uses proximity-based classification: for each course code found in the text,
    scan backward to find the nearest section header and classify the course
    based on whether that header indicates a core or elective section.

    Returns (core_set, elective_set).
    """
    text = program.get('requirements_text', '')
    code_re = re.compile(r'\b([A-Z]{2,5}\s+\d{3,4}[A-Z]?)\b')

    if not text:
        all_codes = {c for c in program.get('courses_mentioned', []) if not c.startswith('HELP')}
        return all_codes, set()

    lower = text.lower()

    # Phrases that precede listings of REQUIRED/CORE courses
    core_markers = [
        'required courses', 'core courses', 'required coursework',
        'core requirements', 'courses designated as', 'following required',
        'must complete', 'fundamentals of', 'required curriculum',
        'required:', 'core:', 'foundation courses',
        # Grad catalog formats
        'program requirements:', 'complete the following', 'required hours',
        'complete all of the following', 'the following courses are required',
        # Breadth / depth sections in grad programs (these are required)
        'breadth component', 'breadth courses', 'breadth requirement',
        'depth component', 'depth courses', 'depth requirement',
        'degree requirements', 'coursework requirements',
        'credits from each of the following',
        'credits from the following',
    ]
    # Phrases that precede listings of ELECTIVE courses
    elective_markers = [
        'concentration in ', 'electives are:', 'elective courses:',
        'choose from', 'select from', 'approved elective',
        'the following electives', 'elective options', 'approved courses',
        'students may choose', 'students may select',
        # Grad catalog formats
        'restricted elective', 'elective hours', 'electives:',
        'elective component', 'elective course',
        'choose one', 'choose two', 'choose three',
    ]

    # Collect all (position, type) for every occurrence of every marker
    section_markers = []
    for m in core_markers:
        pos = 0
        while True:
            p = lower.find(m, pos)
            if p == -1:
                break
            section_markers.append((p, 'core'))
            pos = p + 1
    for m in elective_markers:
        pos = 0
        while True:
            p = lower.find(m, pos)
            if p == -1:
                break
            section_markers.append((p, 'elective'))
            pos = p + 1

    # Find all course codes and their text positions
    code_positions = [
        (match.start(), match.group(1))
        for match in code_re.finditer(text)
        if not match.group(1).startswith('HELP')
    ]

    if not code_positions:
        return set(), set()

    # If no section markers found — fall back to simple first-elective split
    if not section_markers:
        elective_pos = lower.find('elective')
        if 0 < elective_pos < len(text):
            core_codes = {c for p, c in code_positions if p < elective_pos}
            elec_codes = {c for p, c in code_positions if p >= elective_pos}
            return core_codes, elec_codes - core_codes
        return {c for _, c in code_positions}, set()

    core_codes = set()
    elec_codes = set()

    for code_pos, code in code_positions:
        # Find the nearest section marker that appears BEFORE this code
        best_type = None
        best_dist = float('inf')
        for marker_pos, marker_type in section_markers:
            if marker_pos < code_pos:
                dist = code_pos - marker_pos
                if dist < best_dist:
                    best_dist = dist
                    best_type = marker_type

        if best_type == 'elective':
            elec_codes.add(code)
        else:
            # 'core' or no marker found → treat as core (conservative)
            core_codes.add(code)

    # Text is truncated at 4000 chars — elective listings may be cut off.
    # Any course in courses_mentioned that wasn't classified as core = elective.
    all_mentioned = {c for c in program.get('courses_mentioned', []) if not c.startswith('HELP')}
    elec_codes = (elec_codes | (all_mentioned - core_codes))

    return core_codes, elec_codes


def extract_enrolled_program(text):
    """
    Extract just the program the student is enrolled in from natural language.
    E.g. "I am doing my masters in cybersecurity and want data science" → "cybersecurity"
    Ignores career interest words that come after conjunctions.
    Returns a program keyword string, or None if not detected.
    """
    lower = text.lower()
    # Match "masters/phd/bs/mba in [PROGRAM]" and stop before conjunctions/intent words
    stop = r'(?:\s+and\b|\s+but\b|\s+want\b|\s+interest|\s+toward|\s+i\s|\s*,|$)'
    patterns = [
        # "doing/pursuing/studying my masters in [program]"
        r'(?:doing|pursuing|studying|in)\s+(?:my\s+)?'
        r'(?:masters?|ms\b|phd|mba|bachelors?|bs\b|undergrad\w*)\s+in\s+'
        r'([\w][\w ]{1,35}?)' + stop,
        # "masters/phd in [program]"
        r'(?:masters?|ms\b|phd|mba|bachelors?|bs\b)\s+in\s+([\w][\w ]{1,35}?)' + stop,
        # "I'm a [program] student/graduate"
        r"i(?:'m|\s+am)\s+a\s+([\w][\w ]{1,30?})\s+(?:student|graduate|grad\b)",
    ]
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            prog = m.group(1).strip()
            # Drop trailing filler words
            prog = re.sub(r'\s+(?:program|degree|field|major|course)s?$', '', prog).strip()
            if len(prog) > 2:
                return prog
    return None


def find_program_requirements(query):
    """
    Find matching program requirements for a query string.
    Prefers shorter/simpler program names over combined 4+1 or joint programs
    when keyword scores are equal.
    """
    query_lower = query.lower()
    matches = []
    for p in PROGRAM_REQUIREMENTS:
        name_lower = p['name'].lower()
        words = [w for w in re.findall(r'\w+', query_lower) if len(w) > 3]
        score = sum(1 for w in words if w in name_lower)
        if score > 0:
            # Small penalty for long/combined program names so simple
            # "Finance (MS)" beats "Business Analytics/Finance 4+1 (BS/MS)"
            length_penalty = len(name_lower) / 300.0
            matches.append((score - length_penalty, p))
    matches.sort(key=lambda x: -x[0])
    return [m[1] for m in matches[:5]]

# ── Build a summary for the AI system prompt (to avoid token overflow) ──
course_summary = [{"code": c.get("code",""), "title": c.get("title",""), "desc": c.get("description","")[:200]} for c in COURSES_DATA]
jobs_summary   = {prog: [{"title": j["title"], "desc": j["description"]} for j in jobs] for prog, jobs in JOBS_DATA.items()}

_total_jobs = sum(len(v) for v in JOBS_DATA.values())
_jobs_by_prog = {prog: [j['title'] for j in jobs] for prog, jobs in JOBS_DATA.items()}

SYSTEM_PROMPT = f"""You are PathFinder AI — an academic and career advisor exclusively for University of Delaware (UDel) students.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT SCOPE — YOU ONLY ANSWER QUESTIONS ABOUT:
  • UDel courses, programs, and degree requirements
  • Career paths, job roles, and salaries for UDel graduates
  • Elective selection and cross-program exploration
  • Semester planning, prerequisites, and academic roadmaps
  • Internships, skills to develop, and job market demand

If a user asks ANYTHING outside this scope (weather, cooking, general coding help, news, trivia, etc.), respond ONLY with:
"I'm PathFinder AI, designed exclusively for UDel academic and career guidance. I can help you explore UDel courses, career paths, and academic planning. What would you like to know about your UDel journey?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL BEHAVIOR RULES — FOLLOW THESE STRICTLY:
1. NEVER ask clarifying questions about which program the student is in.
   "masters in X" = "X (MS)" grad program. "bachelors in X" = "X (BS)" undergrad. Just proceed.
2. NEVER say "I may have limited data" or "I'm not sure about your exact program."
   You have the official UDel program data injected below — use it.
3. When a student asks about COURSES, answer with COURSES. Do NOT list jobs unless they specifically asked.
4. When a student asks what courses to take to pivot to a different field:
   → List their ★ CORE courses first (mandatory, no choice)
   → Then list their ○ ELECTIVE options that best align with the target field
   → Be specific with course codes and names
5. NEVER say "masters and grad are different" — they are the same thing.

You have deep knowledge of UDel's full course catalog ({len(COURSES_DATA):,} courses) and {_total_jobs} career roles across {len(JOBS_DATA)} programs.

PROGRAM STRUCTURE AWARENESS:
Every UDel program has TWO types of courses:
  ★ CORE (required): courses every student in the program MUST take — these are marked with ★
  ○ ELECTIVES: courses the student CHOOSES from an approved list to fulfill credit requirements

When a student asks about a program, ALWAYS clarify:
  1. What their CORE required courses are (they have no choice — must take these)
  2. What ELECTIVE slots they have (credits they can fill with approved electives)
  3. Which electives align best with their interests or a DIFFERENT career direction

CROSS-PROGRAM EXPLORATION — ELECTIVE STRATEGY (APPLIES TO EVERY PROGRAM):
Every student — regardless of program — stays enrolled in their major but can shape their career direction through elective choices.

CRITICAL RULE — ELECTIVE ADVICE (FOR ALL 26 PROGRAMS):
A student cannot freely enroll in any course they want. They MUST pick electives from their program's APPROVED ELECTIVE LIST (the ○ list).
- The ○ APPROVED ELECTIVES list is injected in the context below for whatever program the student mentions
- From ONLY that list, identify which courses align with the student's desired career field
- If the approved list has limited overlap with the target field, say so honestly and suggest:
  a) Which approved electives are closest to the target field
  b) They speak to their advisor about substituting one technical elective with a course from the target field
- NEVER recommend courses outside the approved elective list as if the student can freely enroll

THIS RULE APPLIES TO ALL PROGRAMS:
- Computer Science student wanting Finance → look at CS approved electives, pick any FINC/ECON/BUAD courses there
- Finance student wanting Data Science → look at Finance approved electives, pick STAT/CISC/DSCC courses there
- Mechanical Engineering student wanting Biomedical → look at MEEG approved electives, pick BMES/BISC courses
- Health Sciences student wanting Research → look at approved electives, pick STAT/research methods courses
- Psychology student wanting Criminal Justice → look at approved electives, pick CRJU/SOCI courses
- ANY program → same logic: core is fixed, electives are the tool for career shaping

HOW TO ANSWER "I'm in [Program X] but want a career in [Field Y]":
  Step 1 → List their ★ CORE courses: "These are mandatory — no choice"
  Step 2 → Show their ○ ELECTIVE slots and the approved list
  Step 3 → From that approved list, pick courses that best align with Field Y
  Step 4 → If few options exist in the approved list, say so and suggest advisor substitution

ALL CAREERS IN PATHFINDER (by program):
{json.dumps(_jobs_by_prog, indent=2)}

RULES:
- Courses 100–499 = undergraduate, 600+ = graduate
- Use ONLY real UDel course codes — never invent course numbers
- Mention salary ranges and demand when relevant
- Keep answers concise with bullet points"""


def course_num(course):
    m = re.search(r'\b(\d{3,4})\b', course.get('title', '') or course.get('code', ''))
    return int(m.group(1)) if m else 0


def match_courses(job_skills, preferred_depts, courses, top_n=6):
    """
    Match courses to a job using a weighted scoring system:
    - Title match: 4 points per skill (very reliable)
    - Description match: 1 point per skill (less reliable)
    - Preferred department bonus: +2 (ensures relevant depts rank higher)
    - Minimum score of 4 required (must match at least one skill in title,
      OR two skills in description, OR be in a preferred dept with a desc match)
    """
    undergrad, grad = [], []
    skills_lower = [s.lower() for s in job_skills]
    preferred_lower = [d.lower() for d in preferred_depts]

    for c in courses:
        desc  = (c.get('description', '') or '').lower()
        title = (c.get('title', '') or '').lower()
        dept  = (c.get('dept', '') or '').lower()

        # Primary skill (first in list) gets 3x bonus to surface the most relevant courses
        primary_bonus = 6 if skills_lower and skills_lower[0] in title else 0
        title_score = sum(4 for s in skills_lower if s in title)
        desc_score  = sum(1 for s in skills_lower if s in desc)
        dept_bonus  = 2 if any(p in dept for p in preferred_lower) else 0

        score = title_score + desc_score + dept_bonus + primary_bonus
        if score < 4:
            continue

        entry = {"title": c.get('title', ''), "code": c.get('code', ''), "score": score}
        if course_num(c) >= 600:
            grad.append(entry)
        else:
            undergrad.append(entry)

    undergrad.sort(key=lambda x: -x['score'])
    grad.sort(key=lambda x: -x['score'])

    def dedupe(lst):
        seen_titles = set()
        out = []
        for e in lst:
            # Normalize: strip dept prefix, lowercase, collapse whitespace
            norm = re.sub(r'^[A-Z]{2,5}\s+\d{3,4}[A-Z]?\s*[-–]\s*', '', e['title']).lower().strip()
            norm = re.sub(r'\s+', ' ', norm)
            if norm not in seen_titles:
                seen_titles.add(norm)
                out.append(e)
        return out

    undergrad = dedupe(undergrad)
    # Dedupe grad separately — do NOT filter out grad courses that share a
    # name with undergrad courses; they are different-level courses (e.g.
    # CPEG 471 vs CPEG 671 "Pen Test and Reverse Engineering").
    grad = dedupe(grad)

    return undergrad[:top_n], grad[:top_n]


# Program → preferred department codes for smarter matching
PROG_DEPTS = {
    "Computer Science":              ["CISC", "CPEG", "ELEG", "MATH"],
    "Artificial Intelligence":       ["CISC", "CPEG", "ELEG", "MATH", "COGN"],
    "Cybersecurity Engineering":     ["CPEG", "CISC", "ELEG", "MISY"],
    "Data Science":                  ["CISC", "MATH", "STAT", "CPEG", "BINF"],
    "Computer Engineering":          ["CPEG", "ELEG", "CISC"],
    "Electrical Engineering":        ["ELEG", "CPEG", "PHYS", "MATH"],
    "Mechanical Engineering":        ["MEEG", "PHYS", "MATH", "CIEG"],
    "Civil Engineering":             ["CIEG", "GEOL", "MEEG", "ENVE"],
    "Chemical Engineering":          ["CHEG", "CHEM", "BISC", "MATH"],
    "Biomedical Engineering":        ["BMES", "BISC", "CHEM", "ELEG", "MEEG"],
    "Management Information Systems":["MISY", "CISC", "ACCT", "BUAD"],
    "Finance":                       ["FINC", "ACCT", "ECON", "MATH", "BUAD"],
    "Accounting":                    ["ACCT", "FINC", "BUAD", "LEST"],
    "Business Administration & Management": ["BUAD", "MISY", "ACCT", "FINC", "MKTG"],
    "Marketing":                     ["BUAD", "COMM", "ECON", "MKTG"],
    "Economics":                     ["ECON", "FINC", "MATH", "STAT", "BUAD"],
    "Health Sciences":               ["NURS", "HLTH", "BISC", "CHEM", "HBNS"],
    "Biological Sciences":           ["BISC", "CHEM", "BIOL", "MMSC", "BIOC"],
    "Chemistry":                     ["CHEM", "BISC", "PHYS", "MATH"],
    "Education":                     ["EDUC", "HDFS", "PSYC", "COMM"],
    "Communication":                 ["COMM", "JOUR", "ENGL", "ARTC"],
    "Political Science & Public Policy": ["POSC", "PLSC", "ECON", "SOCI", "HIST"],
    "Psychology":                    ["PSYC", "CGSC", "HDFS", "SOCI"],
    "Environmental Science":         ["ENSC", "ENVE", "GEOL", "MAST", "BISC"],
    "Agricultural Sciences":         ["ANFS", "PLSC", "ENTM", "AGRI", "FOOD"],
    "Criminal Justice":              ["CRJU", "SOCI", "PSYC", "LEST"],
    # ── New Programs ──
    "Nursing":                       ["NURS", "BISC", "CHEM", "HLTH"],
    "Kinesiology":                   ["KAAP", "BISC", "PHYS", "HLTH", "NTDT"],
    "Statistics":                    ["STAT", "MATH", "CISC"],
    "Applied Mathematics":           ["MATH", "STAT", "CISC", "PHYS"],
    "Neuroscience":                  ["NSCI", "BISC", "PSYC", "CHEM", "KAAP"],
    "Entrepreneurship":              ["ENTR", "BUAD", "FINC", "MKTG", "MISY"],
    "Information Systems":           ["MISY", "CISC", "BUAD", "ACCT"],
    "Physics":                       ["PHYS", "MATH", "CISC", "ELEG"],
    "Philosophy":                    ["PHIL", "ENGL", "POSC", "HIST"],
    "English":                       ["ENGL", "COMM", "HIST", "PHIL"],
    "History":                       ["HIST", "ENGL", "POSC", "SOCI"],
    "Sociology":                     ["SOCI", "PSYC", "CRJU", "HIST"],
    "Biochemistry":                  ["BIOC", "CHEM", "BISC", "MMSC"],
    "Marine Science":                ["MAST", "BISC", "CHEM", "GEOL", "ENSC"],
    "Nutrition & Dietetics":         ["NTDT", "BISC", "CHEM", "HLTH", "KAAP"],
    "Sport Management":              ["SPPA", "BUAD", "ECON", "MKTG"],
    "Hospitality Management":        ["HOSP", "BUAD", "MKTG", "ECON"],
    "Fashion & Design":              ["FASH", "ARTC", "BUAD", "MKTG"],
    "Landscape Architecture":        ["LARC", "ARTC", "ENSC", "PLSC"],
    "Actuarial Sciences":            ["MATH", "STAT", "FINC", "ECON"],
}

# Build PROG_CORE_COURSES and PROG_ELECTIVE_COURSES using text parsing
for _prog_name in PROG_DEPTS:
    _core = set()
    _elec = set()
    for _p in find_program_requirements(_prog_name):
        _pc, _pe = extract_core_elective_codes(_p)
        _core.update(_pc)
        _elec.update(_pe)
    PROG_CORE_COURSES[_prog_name]     = _core
    PROG_ELECTIVE_COURSES[_prog_name] = _elec - _core  # guarantee no overlap

# Pre-build compact job index for search (built once at startup)
JOB_INDEX = []
for _prog, _jobs in JOBS_DATA.items():
    for _j in _jobs:
        JOB_INDEX.append({
            "title": _j["title"],
            "program": _prog,
            "description": _j["description"],
            "demand": _j.get("demand", "Medium"),
            "salary_min": _j.get("salary_min", 0),
            "salary_max": _j.get("salary_max", 0),
        })

# Pre-build compact job list for AI search (title + program only — minimise tokens)
_compact = [{"title": j["title"], "program": j["program"], "demand": j["demand"],
             "salary": f"${j['salary_min']//1000}k-${j['salary_max']//1000}k" if j.get("salary_min") else "varies"}
            for j in JOB_INDEX]
COMPACT_JOB_INDEX_JSON = json.dumps(_compact)

# Pre-build department list at startup
DEPT_LIST = sorted({c.get('dept', '') for c in COURSES_DATA if c.get('dept', '')})

# ── API: Courses ──
@app.route('/api/courses', methods=['GET'])
def get_courses():
    try:
        q     = request.args.get('q', '').lower().strip()
        dept  = request.args.get('dept', '').upper().strip()
        level = request.args.get('level', '')   # 'undergrad' | 'grad' | ''
        page  = int(request.args.get('page', 1))
        per   = 48

        filtered = []
        for c in COURSES_DATA:
            # Level filter
            c_level = c.get('level', 'undergrad')
            if level == 'undergrad' and c_level != 'undergrad': continue
            if level == 'grad'      and c_level != 'grad':      continue

            # Department filter
            if dept and c.get('dept', '') != dept: continue

            # Search filter
            if q:
                title = (c.get('title', '') or '').lower()
                code  = (c.get('code',  '') or '').lower()
                desc  = (c.get('description', '') or '').lower()
                if q not in title and q not in code and q not in desc:
                    continue

            filtered.append(c)

        total = len(filtered)
        start = (page - 1) * per
        page_data = filtered[start:start + per]

        return jsonify({
            "courses": [{"code": c.get("code",""), "title": c.get("title",""),
                         "dept": c.get("dept",""), "level": c.get("level","undergrad"),
                         "description": (c.get("description","") or "")[:300]}
                        for c in page_data],
            "total": total,
            "page": page,
            "pages": (total + per - 1) // per,
            "depts": DEPT_LIST
        })
    except Exception as e:
        print(f"COURSES ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# ── API: Stats ──
@app.route('/api/stats', methods=['GET'])
def stats():
    total_jobs = sum(len(v) for v in JOBS_DATA.values())
    return jsonify({
        "courses": len(COURSES_DATA),
        "jobs": total_jobs,
        "programs": len(JOBS_DATA)
    })


# ── API: Smart Search ──
@app.route('/api/search', methods=['POST'])
def smart_search():
    try:
        query = request.get_json().get('query', '').strip()
        if not query:
            return jsonify({"results": [], "interpreted_as": ""})

        from rag.retriever import search_careers as faiss_search_careers

        # FAISS semantic retrieval — over-fetch to allow title-level dedup
        raw_results = faiss_search_careers(query, k=40)

        # Deduplicate by title (same job title can appear in multiple programs),
        # keeping the highest-scoring occurrence
        seen: dict[str, dict] = {}
        for career in raw_results:
            title = career.get("title", "")
            if title not in seen or career["score"] > seen[title]["score"]:
                seen[title] = career

        top_results = sorted(seen.values(), key=lambda x: -x["score"])[:10]

        enriched = [
            {
                "title": c.get("title", ""),
                "program": c.get("program", ""),
                "description": c.get("description", ""),
                "demand": c.get("demand", "Medium"),
                "salary_min": c.get("salary_min", 0),
                "salary_max": c.get("salary_max", 0),
            }
            for c in top_results
        ]

        return jsonify({"results": enriched, "interpreted_as": f"Showing careers related to: {query}"})
    except Exception as e:
        print(f"SEARCH ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# ── Pre-compute career paths at startup (cached) ──
def _build_career_paths():
    result = {}
    for program, jobs in JOBS_DATA.items():
        preferred = PROG_DEPTS.get(program, [])
        core_set = PROG_CORE_COURSES.get(program, set())
        result[program] = []
        for job in jobs:
            ug, gr = match_courses(job.get('skills', []), preferred, COURSES_DATA, top_n=10)
            for c in ug + gr:
                c['is_core'] = c.get('code', '') in core_set
            result[program].append({
                "title": job['title'],
                "description": job['description'],
                "salary_min": job.get('salary_min', 0),
                "salary_max": job.get('salary_max', 0),
                "demand": job.get('demand', 'Medium'),
                "undergrad_courses": ug,
                "grad_courses": gr
            })
    print(f"  Career paths cached: {sum(len(v) for v in result.values())} jobs across {len(result)} programs")
    return result

CAREER_PATHS_CACHE = _build_career_paths()

# ── API: Career paths ──
@app.route('/api/career-paths', methods=['GET'])
def get_career_paths():
    return jsonify(CAREER_PATHS_CACHE)


# ── API: AI Course Match ──
@app.route('/api/ai-match', methods=['POST'])
def ai_match():
    try:
        body      = request.get_json()
        job_title = body.get('job_title', '')
        program   = body.get('program', '')

        cache_key = f"{program}::{job_title}"
        if cache_key in AI_MATCH_CACHE:
            return jsonify(AI_MATCH_CACHE[cache_key])

        # Find the job
        job = next((j for j in JOBS_DATA.get(program, []) if j['title'] == job_title), None)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        from rag.retriever import search_courses as faiss_search_courses

        preferred = PROG_DEPTS.get(program, [])
        core_set = PROG_CORE_COURSES.get(program, set())

        # Build semantic query from job skills + description
        skills_str = ", ".join(job.get("skills", []))
        query = f"{job_title} {skills_str} {job.get('description', '')[:200]}"

        # FAISS retrieval filtered by preferred departments and level
        ug_results = faiss_search_courses(
            query, k=8,
            filters={"level": "undergrad", "preferred_depts": preferred},
        )
        grad_results = faiss_search_courses(
            query, k=8,
            filters={"level": "grad", "preferred_depts": preferred},
        )

        result = {
            "undergrad_courses": [
                {
                    "title": c.get("title", ""),
                    "score": 99,
                    "is_core": c.get("code", "") in core_set,
                }
                for c in ug_results
            ],
            "grad_courses": [
                {
                    "title": c.get("title", ""),
                    "score": 99,
                    "is_core": c.get("code", "") in core_set,
                }
                for c in grad_results
            ],
        }
        AI_MATCH_CACHE[cache_key] = result
        return jsonify(result)
    except Exception as e:
        print(f"AI MATCH ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# ── API: Roadmap ──
@app.route('/api/roadmap', methods=['POST'])
def roadmap():
    try:
        body      = request.get_json()
        major     = body.get('major', '')
        career    = body.get('career', '')
        year      = body.get('year', 'Freshman')
        courses   = body.get('completed_courses', '')

        # Year configuration
        YEAR_CONFIG = {
            "Freshman":       {"year_num": 1, "is_grad": False, "focus": "100–200 level (introductory)", "completed_below": 0},
            "Sophomore":      {"year_num": 2, "is_grad": False, "focus": "200–300 level (foundational)", "completed_below": 200},
            "Junior":         {"year_num": 3, "is_grad": False, "focus": "300–400 level (intermediate/advanced)", "completed_below": 300},
            "Senior":         {"year_num": 4, "is_grad": False, "focus": "400+ level (capstone/advanced)", "completed_below": 400},
            "Graduate Year 1":{"year_num": 1, "is_grad": True,  "focus": "600–700 level (core graduate)", "completed_below": 0},
            "Graduate Year 2":{"year_num": 2, "is_grad": True,  "focus": "700–800+ level (advanced graduate)", "completed_below": 700},
        }
        cfg      = YEAR_CONFIG.get(year, YEAR_CONFIG["Freshman"])
        is_grad  = cfg["is_grad"]
        year_num = cfg["year_num"]
        focus    = cfg["focus"]
        cutoff   = cfg["completed_below"]

        # Inject real program requirements from PROGRAM_INFO_CACHE
        prog_info = PROGRAM_INFO_CACHE.get(major, {})
        if is_grad:
            core_entries = prog_info.get('core_grad', [])
            elec_entries = prog_info.get('electives_grad', [])
        else:
            core_entries = prog_info.get('core_undergrad', [])
            elec_entries = prog_info.get('electives_undergrad', [])

        def fmt_entries(entries):
            return '\n  '.join(
                f"{e['code']} — {e['title']}" for e in entries
            ) if entries else '(none)'

        # Auto-compute completed courses based on year level
        def course_num(code):
            m = re.search(r'(\d{3,4})', code)
            return int(m.group(1)) if m else 0

        all_program_courses = core_entries + elec_entries
        auto_completed = [e['code'] for e in all_program_courses if course_num(e['code']) < cutoff] if cutoff > 0 else []

        # For Grad Year 2: also mark Year 1 grad core as completed
        if year == "Graduate Year 2" and core_entries:
            auto_completed += [e['code'] for e in core_entries if e['code'] not in auto_completed]

        # Merge auto-completed with manually entered
        manual_completed = [c.strip() for c in courses.split(',') if c.strip()] if courses else []
        all_completed = list(dict.fromkeys(auto_completed + manual_completed))  # dedupe, preserve order
        completed_str = ', '.join(all_completed) if all_completed else 'None'

        req_context = ""
        if core_entries or elec_entries:
            req_context = (
                f"\n\nOFFICIAL UDEL {major} COURSES:\n"
                f"★ CORE (required — use these first):\n  {fmt_entries(core_entries)}\n"
                f"○ ELECTIVES (pick career-aligned ones):\n  {fmt_entries(elec_entries)}\n"
                f"RULE: Use ONLY these course codes. Do NOT invent any course numbers.\n"
            )

        year_label = f"Graduate Year {year_num}" if is_grad else f"Year {year_num} ({year})"
        prompt = f"""You are a professional academic advisor at the University of Delaware.
Build a 2-semester course plan for ONE specific academic year of this student's program.

STUDENT PROFILE:
- Major: {major}
- Career Goal: {career}
- Current Standing: {year}
- Already Completed (do NOT repeat these): {completed_str}
{req_context}
PLANNING RULES:
1. Output EXACTLY 2 semesters — Fall and Spring of {year_label} ONLY. No other years.
2. Each semester: 3–5 courses (12–16 credits).
3. ONLY use course codes from the CORE and ELECTIVES lists above. NEVER invent codes.
4. Do NOT include any already-completed courses listed above.
5. Focus on {focus} courses — these are appropriate for a {year} student. Avoid courses far outside this level range.
6. Pick courses that make sense for this specific year: not too advanced for a {year}, not too basic either.
7. ELECTIVES: ONLY pick electives that DIRECTLY build skills for {career}. Skip irrelevant ones.
8. For each course, write exactly one sentence explaining how it specifically builds skills for {career}.

Return ONLY valid JSON, no markdown, no explanation:
{{
  "semesters": [
    {{
      "label": "{year} – Fall",
      "season": "Fall",
      "year": {year_num},
      "courses": [
        {{"code": "DEPT 101", "name": "Full Course Name", "credits": 3, "why": "Specific reason this course prepares for {career}."}}
      ]
    }}
  ],
  "outlook": "2–3 sentences on career prospects, typical starting salary, and growth path for {career} graduates from UDel."
}}"""

        from rag import pipeline as rag_pipeline
        data = rag_pipeline.generate_roadmap(prompt, SYSTEM_PROMPT, career, major)
        return jsonify({"roadmap_json": data})
    except ValueError as ve:
        print(f"ROADMAP JSON ERROR: {ve}")
        return jsonify({"error": "Could not generate roadmap. Please try again."}), 500
    except Exception as e:
        err = str(e)
        print(f"ROADMAP ERROR: {err}")
        if '429' in err or 'quota' in err.lower() or 'rate' in err.lower():
            return jsonify({"error": "AI rate limit reached — please try again in a minute or switch to a different model."}), 429
        return jsonify({"error": "Could not generate roadmap. Please try again."}), 500


# ── API: Chat ──
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        body = request.get_json()
        messages = body.get('messages', [])

        # Combine last user message + recent conversation for program detection
        last_user_msg = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), '')
        recent_context = ' '.join(m['content'] for m in messages[-6:] if m.get('role') == 'user')
        search_text = last_user_msg + ' ' + recent_context

        program_context = ""
        seen_prog_names = set()
        unique_progs = []

        # First: try to extract the program the student is ENROLLED IN specifically
        # (avoids matching their target interest like "data science" over their actual program)
        enrolled_kw = extract_enrolled_program(search_text)
        if enrolled_kw:
            for p in find_program_requirements(enrolled_kw):
                if p['name'] not in seen_prog_names:
                    seen_prog_names.add(p['name'])
                    unique_progs.append(p)

        # Also add any additional programs mentioned (target field, etc.)
        for p in find_program_requirements(search_text):
            if p['name'] not in seen_prog_names:
                seen_prog_names.add(p['name'])
                unique_progs.append(p)

        if unique_progs:
            program_context = "\n\n=== OFFICIAL UDEL PROGRAM DATA (USE THESE ONLY — DO NOT INVENT COURSES) ===\n"
            for p in unique_progs[:3]:
                core_codes, elec_codes = extract_core_elective_codes(p)
                program_context += f"\n**{p['name']}** ({p['level_type']})"
                if p.get('total_credits'):
                    program_context += f"  |  {p['total_credits']} total credits\n"
                else:
                    program_context += "\n"
                def fmt_codes(codes):
                    parts = []
                    for code in sorted(codes):
                        raw = COURSE_CODE_TO_TITLE.get(code, '')
                        # Strip redundant "DEPT ### - " prefix from stored title
                        name = re.sub(r'^[A-Z]{2,5}\s+\d{3,4}[A-Z]?\s*[-–]\s*', '', raw)
                        parts.append(f"{code} — {name}" if name else code)
                    return '\n    '.join(parts)

                if core_codes:
                    program_context += f"  ★ CORE (required — must take ALL):\n    {fmt_codes(core_codes)}\n"
                if elec_codes:
                    program_context += f"  ○ APPROVED ELECTIVES (pick from this list):\n    {fmt_codes(elec_codes)}\n"
                elif not core_codes:
                    all_codes = [c for c in p.get('courses_mentioned', []) if not c.startswith('HELP')]
                    program_context += f"  Courses in program:\n    {fmt_codes(all_codes)}\n"
            program_context += (
                "\nCRITICAL INSTRUCTION: "
                "When recommending electives, ONLY suggest courses from the ○ APPROVED ELECTIVES list above. "
                "The student CANNOT freely enroll in any graduate course — they must pick from their program's approved list. "
                "If the student wants to align electives with a different field (e.g. data science), "
                "identify which approved electives from the ○ list best match that field. "
                "If the approved list has very few relevant courses, say so and suggest they ask their advisor "
                "about substituting a technical elective.\n"
            )

        system = SYSTEM_PROMPT + program_context

        from rag import pipeline as rag_pipeline
        reply = rag_pipeline.answer_chat(last_user_msg, {}, messages, system)
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"CHAT ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# ── Pre-compute program info at startup ──
def _build_program_info():
    """
    Build accurate course lists for each program using:
    1. Undergrad: real scraped data from program_courses.json (UDel Major Finder)
    2. Grad: real scraped data from program_requirements.json (UDel Grad Catalog)
    Falls back to dept-based filtering only when no scraped data is available.
    """

    # Build fast code → course lookup
    code_to_course = {}
    for c in COURSES_DATA:
        code = c.get('code', '').strip()
        if code:
            code_to_course[code] = c

    # Build grad course lookup: exact program name substrings → best matching grad program
    # Use specific names verified against program_requirements.json to avoid wrong matches
    GRAD_PROGRAM_KEYWORDS = {
        "Computer Science":              ["Computer and Information Sciences (MS)"],
        "Artificial Intelligence":       ["Artificial Intelligence (MS)"],
        "Cybersecurity Engineering":     ["Cybersecurity (MS)"],
        "Data Science":                  ["Computer and Information Sciences (MS)", "Applied Statistics (MS)"],
        "Computer Engineering":          ["Electrical and Computer Engineering - Thesis (MS)", "Electrical and Computer Engineering - Non-Thesis (MS)"],
        "Electrical Engineering":        ["Electrical and Computer Engineering - Thesis (MS)", "Electrical and Computer Engineering - Non-Thesis (MS)"],
        "Mechanical Engineering":        ["Mechanical Engineering (MSME)"],
        "Civil Engineering":             ["Civil Engineering - Structural Engineering Concentration (MCE)", "Civil Engineering - Environmental Engineering Concentration (MCE)"],
        "Chemical Engineering":          ["Chemical Engineering (MChE)"],
        "Biomedical Engineering":        ["Biopharmaceutical Sciences - Bioprocess Development Concentration (MS)", "Medical and Molecular Sciences (MS)"],
        "Management Information Systems":["Business Analytics and Information Management (MS)"],
        "Finance":                       ["Finance (MS)"],
        "Accounting":                    ["Accounting (MS)", "Accounting Analytics (MS)"],
        "Marketing":                     ["Business Administration (MBA)", "Strategic Communication (MA)"],
        "Economics":                     ["Economics and Applied Econometrics (MS)"],
        "Health Sciences":               ["Clinical Health Science (MS)", "Community Health and Behavior (MPH)"],
        "Biological Sciences":           ["Biological Sciences - Cell and Organ Systems Concentration (MS)", "Biological Sciences - Molecular Biology and Genetics Concentration (MS)"],
        "Chemistry":                     ["Chemistry and Biochemistry (MS)"],
        "Biochemistry":                  ["Chemistry and Biochemistry (MS)"],
        "Education":                     ["Educational Technology (MEd)", "Teacher Leadership (MEd)"],
        "Communication":                 ["Communication (MA)", "Strategic Communication (MA)"],
        "Political Science & Public Policy": ["Political Science and International Relations (MA)", "Public Policy (MPP)"],
        "Psychology":                    ["Psychological and Brain Sciences - Clinical Science Concentration (PhD)", "Clinical Psychological Science (MS)"],
        "Environmental Science":         ["Environmental Science and Management (MS)", "Energy and Environmental Policy (MEEP)"],
        "Criminal Justice":              ["Criminology (MA)"],
        "Nursing":                       ["Nursing - Family/Individual Across the Lifespan Nurse Practitioner Concentration (MSN)", "Nursing Education (MSN)"],
        "Kinesiology":                   ["Exercise Science (MS)", "Athletic Training (MS)", "Biomechanics and Movement Science (MS)"],
        "Statistics":                    ["Statistics (MS)", "Applied Statistics (MS)"],
        "Applied Mathematics":           ["Applied Mathematics (MS)", "Mathematics (MS)"],
        "Neuroscience":                  ["Medical and Molecular Sciences (MS)", "Psychological and Brain Sciences - Behavioral Neuroscience Concentration (PhD)"],
        "Entrepreneurship":              ["Business Administration (MBA)"],
        "Information Systems":           ["Business Analytics and Information Management (MS)"],
        "Physics":                       ["Physics (MS)"],
        "Sociology":                     ["Sociology (MA)"],
        "Marine Science":                ["Marine Studies - Oceanography Concentration (MS)", "Marine Studies - Marine BioSciences Concentration (PhD)"],
        "Nutrition & Dietetics":         ["Nutrition and Dietetics (MS) with Dietetics Internship (DI)", "Nutrition Science (PhD)"],
        "Sport Management":              ["Athletic Training (MS)", "Exercise Science (MS)"],
        "Fashion & Design":              ["Fashion and Apparel Studies (MS)"],
        "Actuarial Sciences":            ["Statistics (MS)", "Applied Statistics (MS)"],
    }

    NOISE_CODES = {'HELP 2025', 'HELP 2026', 'HELP 2024'}
    NOISE_TITLES = {'SPECIAL PROBLEM', 'SEMINAR', 'ONCOURSE SUBSTITUTION', 'INDEPENDENT STUDY',
                    'INTERNSHIP', 'THESIS', 'DISSERTATION', 'WORKSHOP', 'PRACTICUM',
                    'SPECIAL TOPICS', 'DIRECTED STUDY', 'RESEARCH'}

    def sort_key(entry):
        m = re.search(r'\d+', entry.get('code', ''))
        return int(m.group()) if m else 0

    def make_entry(c):
        title_raw = c.get('title', '')
        title = re.sub(r'^[A-Z]{2,5}\s+\d{3,4}[A-Z]?\s*[-–]\s*', '', title_raw)
        return {'code': c.get('code', ''), 'title': title or c.get('code', '')}

    def codes_to_entries(codes):
        """Convert list of course codes to course entry dicts, using all_courses.json for titles."""
        entries = []
        seen = set()
        for code in codes:
            if code in NOISE_CODES or code in seen:
                continue
            seen.add(code)
            if code in code_to_course:
                entries.append(make_entry(code_to_course[code]))
            else:
                # Code not in our DB — still show it with code only
                entries.append({'code': code, 'title': code})
        return sorted(entries, key=sort_key)

    def get_grad_courses(prog_name):
        """
        Get grad courses (core + electives) from program_requirements.json.
        Uses extract_core_elective_codes() on requirements_text to split
        into core vs elective courses.
        Collects from ALL matching programs (supports multi-program mappings).
        Returns (core_entries, elective_entries).
        """
        keywords = GRAD_PROGRAM_KEYWORDS.get(prog_name, [])
        if not keywords:
            return [], []

        # Find all matching programs (not just the best one)
        matches = []
        for req in PROGRAM_REQUIREMENTS:
            if req.get('level_type') != 'grad':
                continue
            req_name = req.get('name', '')
            if any(skip in req_name for skip in ('4+1', '3+2', 'Certificate', 'MBA/')):
                continue
            if '/' in req_name and 'MBA/' not in req_name:
                continue
            score = sum(1 for kw in keywords if kw.lower() in req_name.lower())
            if score > 0:
                matches.append(req)

        if not matches:
            return [], []

        # Collect grad courses (core + electives) from all matching programs
        grad_core = []
        grad_elec = []
        seen = set()
        # Dept whitelist: only allow relevant departments per program (prevents MUSC, ACCT, etc.)
        DEPT_WHITELIST = {
            "Computer Science":              {"CISC", "CPEG", "MATH", "STAT"},
            "Artificial Intelligence":       {"CISC", "CPEG", "ELEG", "MATH", "STAT"},
            "Cybersecurity Engineering":     {"CISC", "CPEG", "ELEG", "MATH"},
            "Computer Engineering":          {"CISC", "CPEG", "ELEG", "MATH"},
            "Electrical Engineering":        {"ELEG", "CPEG", "CISC", "MATH", "PHYS"},
            "Mechanical Engineering":        {"MEEG", "CISC", "MATH", "PHYS", "CHEG"},
            "Civil Engineering":             {"CIEG", "MATH", "GEOL", "PHYS", "ENSC"},
            "Chemical Engineering":          {"CHEG", "CHEM", "MATH", "PHYS", "BIOC"},
            "Biomedical Engineering":        {"BIOM", "CISC", "CHEM", "MATH", "PHYS", "BISC"},
            "Data Science":                  {"CISC", "STAT", "MATH", "CPEG", "ELEG"},
            "Finance":                       {"FINC", "ECON", "ACCT", "BUAD", "STAT"},
            "Accounting":                    {"ACCT", "FINC", "BUAD", "ECON"},
            "Marketing":                     {"MISY", "BUAD", "ECON", "FINC"},
            "Economics":                     {"ECON", "STAT", "MATH", "FINC"},
            "Management Information Systems":{"MISY", "CISC", "BUAD", "ACCT", "STAT"},
            "Business Administration & Management": {"BUAD", "MISY", "FINC", "ACCT", "ECON"},
        }
        allowed_depts = DEPT_WHITELIST.get(prog_name, set())

        for match in matches:
            core_codes, elec_codes = extract_core_elective_codes(match)
            core_codes = {c for c in core_codes if c not in NOISE_CODES}
            elec_codes = {c for c in elec_codes if c not in NOISE_CODES}

            # Fallback: if no split detected, treat all as core
            if not core_codes and not elec_codes:
                core_codes = {c for c in match.get('courses_mentioned', []) if c not in NOISE_CODES}

            for c in match.get('courses_mentioned', []):
                if c in seen:
                    continue
                m = re.search(r'(\d{3,4})', c)
                if not m or int(m.group(1)) < 500:
                    continue
                # Filter out irrelevant departments when whitelist exists
                if allowed_depts:
                    dept = re.match(r'([A-Z]+)', c)
                    if dept and dept.group(1) not in allowed_depts:
                        continue
                seen.add(c)
                if c in core_codes:
                    grad_core.append(c)
                elif c in elec_codes:
                    grad_elec.append(c)

        return codes_to_entries(grad_core[:20]), codes_to_entries(grad_elec[:25])

    result = {}
    for prog_name in PROG_DEPTS:
        # ── Undergrad: use official curriculum data ──
        prog_data = PROGRAM_COURSES.get(prog_name, {})
        ug_codes = prog_data.get('undergrad', [])
        ug_elec_codes = prog_data.get('undergrad_electives', [])

        # Use scraped data only if we have enough courses (≥10); otherwise dept-based is richer
        if len(ug_codes) >= 10:
            # Core = required program courses from official curriculum
            core_ug = codes_to_entries(ug_codes)

            if ug_elec_codes:
                # Use official electives if we have them
                elec_ug = codes_to_entries(ug_elec_codes)[:25]
            else:
                # Supplement: find electives from program departments not in core
                core_code_set = set(ug_codes)
                all_depts = set(PROG_DEPTS.get(prog_name, []))
                elec_ug = []
                for c in COURSES_DATA:
                    code = c.get('code', '').strip()
                    if not code or code in core_code_set or code in NOISE_CODES:
                        continue
                    if c.get('level', 'undergrad') != 'undergrad':
                        continue
                    dept = c.get('dept', '')
                    if dept not in all_depts:
                        continue
                    m = re.search(r'(\d{3,4})', code)
                    if m and int(m.group(1)) >= 200:
                        elec_ug.append(make_entry(c))
                elec_ug = sorted(elec_ug, key=sort_key)[:25]
        else:
            # Dept-based filtering for programs with sparse scraped data
            primary_dept = PROG_DEPTS[prog_name][0]
            secondary_depts = set(PROG_DEPTS[prog_name][1:])
            core_ug, elec_ug = [], []
            for c in COURSES_DATA:
                if c.get('level', 'undergrad') != 'undergrad':
                    continue
                code = c.get('code', '').strip()
                if not code or code in NOISE_CODES:
                    continue
                # Filter junk titles
                title_upper = c.get('title', '').upper()
                if any(noise in title_upper for noise in NOISE_TITLES):
                    continue
                # Only include numbered courses 100+
                m = re.search(r'(\d{3,4})', code)
                if not m or int(m.group(1)) < 100:
                    continue
                dept = c.get('dept', '')
                entry = make_entry(c)
                if dept == primary_dept:
                    core_ug.append(entry)
                elif dept in secondary_depts:
                    elec_ug.append(entry)
            core_ug = sorted(core_ug, key=sort_key)[:25]
            elec_ug = sorted(elec_ug, key=sort_key)[:20]

        # ── Grad: always prefer scraped catalog data from program_requirements.json ──
        grad_core, grad_elec = get_grad_courses(prog_name)
        # Fall back to program_courses.json grad data if catalog had nothing
        if not grad_core and not grad_elec and prog_data.get('grad_core'):
            grad_core = codes_to_entries(prog_data['grad_core'])
            grad_elec = codes_to_entries(prog_data.get('grad_electives', []))

        result[prog_name] = {
            'core_undergrad': core_ug,
            'electives_undergrad': elec_ug,
            'core_grad': grad_core,
            'electives_grad': grad_elec,
            'total_credits': None
        }

    return result

PROGRAM_INFO_CACHE = _build_program_info()
print(f"  Program info cached: {len(PROGRAM_INFO_CACHE)} programs")


# ── API: Program Info ──
@app.route('/api/program-info', methods=['GET'])
def program_info():
    return jsonify(PROGRAM_INFO_CACHE)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"PathFinder Server starting on port {port}")
    print(f"  Courses loaded: {len(COURSES_DATA)}")
    print(f"  Programs loaded: {len(JOBS_DATA)}")
    total_jobs = sum(len(v) for v in JOBS_DATA.values())
    print(f"  Job roles loaded: {total_jobs}")
    app.run(debug=False, host="0.0.0.0", port=port)
