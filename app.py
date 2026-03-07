from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import re
import anthropic

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

@app.route('/')
def index():
    return app.send_static_file('index.html')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

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
    ]
    # Phrases that precede listings of ELECTIVE courses
    elective_markers = [
        'concentration in ', 'electives are:', 'elective courses:',
        'choose from', 'select from', 'approved elective',
        'the following electives', 'elective options', 'approved courses',
        'students may choose', 'students may select',
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
    return undergrad[:top_n], grad[:top_n]


# Program → preferred department codes for smarter matching
PROG_DEPTS = {
    "Computer Science":              ["CISC", "CPEG", "ELEG", "MATH"],
    "Artificial Intelligence":       ["CISC", "CPEG", "ELEG", "MATH", "COGN"],
    "Cybersecurity Engineering":     ["CPEG", "CISC", "ELEG", "MISY"],
    "Data Science":                  ["CISC", "MATH", "STAT", "ECON", "DSCC"],
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
    "Marketing":                     ["MKTG", "BUAD", "COMM", "ECON"],
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

        # Send compact index to Claude — titles + programs only to save tokens
        compact = [{"title": j["title"], "program": j["program"], "demand": j["demand"],
                    "salary": f"${j['salary_min']//1000}k-${j['salary_max']//1000}k" if j.get("salary_min") else "varies"}
                   for j in JOB_INDEX]

        prompt = (
            f'A University of Delaware student searched PathFinder for: "{query}"\n\n'
            f'Understand their INTENT — handle typos, natural language, vague requests:\n'
            f'- "high paying jobs" → prioritize High demand + high salary\n'
            f'- "I like helping people" → healthcare, education, social work\n'
            f'- "data engneer" (typo) → Data Engineer\n'
            f'- "something creative" → marketing, communication, design roles\n'
            f'- "government jobs" → policy, criminal justice, public sector\n\n'
            f'Available careers (520 total):\n{json.dumps(compact)}\n\n'
            f'Return the top 10 most relevant careers. Also write 1 sentence explaining what you understood.\n'
            f'Respond ONLY with JSON:\n'
            f'{{"results": ["Job Title 1", "Job Title 2", ...], "interpreted_as": "I understood you want..."}}'
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        parsed = json.loads(text.strip())

        # Enrich results with full job data
        title_to_job = {j["title"]: j for j in JOB_INDEX}
        enriched = []
        for title in parsed.get("results", []):
            if title in title_to_job:
                enriched.append(title_to_job[title])

        return jsonify({"results": enriched, "interpreted_as": parsed.get("interpreted_as", "")})
    except Exception as e:
        print(f"SEARCH ERROR: {e}")
        return jsonify({"error": str(e)}), 500


# ── API: Career paths ──
@app.route('/api/career-paths', methods=['GET'])
def get_career_paths():
    try:
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
        return jsonify(result)
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"error": str(e)}), 500


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

        # Send ALL courses from preferred departments — Claude picks freely
        preferred = PROG_DEPTS.get(program, [])
        preferred_lower = [d.lower() for d in preferred]

        ug_pool, grad_pool = [], []
        for c in COURSES_DATA:
            dept = (c.get('dept', '') or '').lower()
            if not any(p in dept for p in preferred_lower):
                continue
            title = c.get('title', '')
            num = course_num(c)
            if num >= 600:
                grad_pool.append(title)
            elif num >= 100:
                ug_pool.append(title)

        prompt = (
            f'You are a UDel academic advisor. A student is pursuing "{job_title}" ({program}).\n'
            f'Job description: {job.get("description", "")}\n'
            f'Key skills needed: {", ".join(job.get("skills", []))}\n\n'
            f'From the FULL UDel course catalog for this program below, select the BEST 8 undergraduate '
            f'and BEST 8 graduate courses that genuinely prepare a student for this career.\n'
            f'Choose courses that build real, job-relevant skills — not just intro courses.\n\n'
            f'Undergraduate courses available ({len(ug_pool)} total):\n{json.dumps(ug_pool)}\n\n'
            f'Graduate courses available ({len(grad_pool)} total):\n{json.dumps(grad_pool)}\n\n'
            f'Respond ONLY with valid JSON, no markdown:\n'
            f'{{"undergrad": ["exact title from list", ...], "grad": ["exact title from list", ...]}}'
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        parsed = json.loads(text.strip())

        ug_set   = set(ug_pool)
        grad_set = set(grad_pool)
        core_set = PROG_CORE_COURSES.get(program, set())
        result = {
            "undergrad_courses": [{"title": t, "score": 99,
                                   "is_core": COURSE_TITLE_TO_CODE.get(t, '') in core_set}
                                  for t in parsed.get("undergrad", []) if t in ug_set],
            "grad_courses":      [{"title": t, "score": 99,
                                   "is_core": COURSE_TITLE_TO_CODE.get(t, '') in core_set}
                                  for t in parsed.get("grad", []) if t in grad_set]
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

        # Inject real program requirements (with core/elective split) if available
        prog_reqs = find_program_requirements(f"{major} {career}")
        req_context = ""
        if prog_reqs:
            p = prog_reqs[0]
            core_codes, elec_codes = extract_core_elective_codes(p)
            def fmt(codes):
                parts = []
                for code in sorted(codes):
                    raw = COURSE_CODE_TO_TITLE.get(code, '')
                    name = re.sub(r'^[A-Z]{2,5}\s+\d{3,4}[A-Z]?\s*[-–]\s*', '', raw)
                    parts.append(f"{code} — {name}" if name else code)
                return '\n  '.join(parts)

            req_context = (
                f"\n\nOFFICIAL UDEL PROGRAM DATA for {p['name']}:\n"
                f"Total Credits: {p.get('total_credits', 'unknown')}\n"
                f"★ CORE (must take all):\n  {fmt(core_codes)}\n"
                f"○ ELECTIVES (choose from):\n  {fmt(elec_codes)}\n"
                f"RULE: Use ONLY these real course codes. Do NOT invent course numbers.\n"
                f"RULE: Schedule CORE courses first — they are mandatory. Fill elective slots with courses aligned to {career}.\n"
            )

        prompt = f"""A University of Delaware student wants a semester-by-semester course roadmap.

Student Profile:
- Major: {major}
- Target Career: {career}
- Current Year: {year}
- Completed Courses: {courses if courses else 'None listed'}
{req_context}
Rules:
- Use ONLY real UDel course codes from the official program data above
- Respect prerequisites — intro courses before advanced ones
- Do NOT include courses already completed
- Start from {year} through graduation

Format EXACTLY like this:
**Year X – Fall/Spring**
- DEPT XXX - Course Name: [one sentence why this matters for {career}]

Include 4-5 courses per semester. End with a 2-sentence career outlook for {career}."""

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return jsonify({"roadmap": response.content[0].text})
    except Exception as e:
        print(f"ROADMAP ERROR: {e}")
        return jsonify({"error": str(e)}), 500


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

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=system,
            messages=messages
        )
        return jsonify({"reply": response.content[0].text})
    except Exception as e:
        print(f"CHAT ERROR: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"PathFinder Server starting on port {port}")
    print(f"  Courses loaded: {len(COURSES_DATA)}")
    print(f"  Programs loaded: {len(JOBS_DATA)}")
    total_jobs = sum(len(v) for v in JOBS_DATA.values())
    print(f"  Job roles loaded: {total_jobs}")
    app.run(debug=False, host="0.0.0.0", port=port)
