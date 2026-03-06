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

# ── Build a summary for the AI system prompt (to avoid token overflow) ──
course_summary = [{"code": c.get("code",""), "title": c.get("title",""), "desc": c.get("description","")[:200]} for c in COURSES_DATA]
jobs_summary   = {prog: [{"title": j["title"], "desc": j["description"]} for j in jobs] for prog, jobs in JOBS_DATA.items()}

SYSTEM_PROMPT = f"""You are PathFinder AI, built into PathFinder — a career mapping tool for University of Delaware students.

You can answer ANY question — general knowledge, coding, career advice, study tips, anything. You are a fully capable general-purpose AI.

You also have deep knowledge of UDel's full course catalog (2,325 courses across all departments) and 188 career roles spanning every industry. Use this to give specific, actionable advice.

UDel Programs covered: {list(JOBS_DATA.keys())}

Sample career roles available: Software Engineer, Data Scientist, Nurse Practitioner, Civil Engineer, Policy Analyst, Investment Banker, Marine Biologist, Teacher, and 180+ more.

When answering career/course questions:
- Be specific — mention actual course codes (e.g., CISC 481, CHEM 321)
- Courses numbered 100-499 = undergraduate, 600+ = graduate
- Give semester-by-semester advice when asked for a roadmap
- Mention expected salary ranges and job market demand when relevant
- Keep answers concise, use bullet points for lists"""


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

        entry = {"title": c.get('title', ''), "score": score}
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

# ── API: Career paths ──
@app.route('/api/career-paths', methods=['GET'])
def get_career_paths():
    try:
        result = {}
        for program, jobs in JOBS_DATA.items():
            preferred = PROG_DEPTS.get(program, [])
            result[program] = []
            for job in jobs:
                ug, gr = match_courses(job.get('skills', []), preferred, COURSES_DATA, top_n=10)
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

        # Get keyword candidates first (wider pool for Claude to choose from)
        preferred = PROG_DEPTS.get(program, [])
        ug_candidates, grad_candidates = match_courses(job.get('skills', []), preferred, COURSES_DATA, top_n=25)

        prompt = (
            f'You are a UDel career advisor. A student is targeting: "{job_title}" (from {program} program).\n'
            f'Job description: {job.get("description", "")}\n\n'
            f'From the candidate courses below, pick the BEST 8 undergraduate and BEST 8 graduate courses '
            f'that genuinely build skills for this specific career. Order by importance.\n\n'
            f'Undergraduate candidates:\n{json.dumps([c["title"] for c in ug_candidates])}\n\n'
            f'Graduate candidates:\n{json.dumps([c["title"] for c in grad_candidates])}\n\n'
            f'Respond ONLY with JSON (no markdown):\n'
            f'{{"undergrad": ["exact course title", ...], "grad": ["exact course title", ...]}}'
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        parsed = json.loads(text.strip())

        ug_titles  = {c['title'] for c in ug_candidates}
        grad_titles = {c['title'] for c in grad_candidates}
        result = {
            "undergrad_courses": [{"title": t, "score": 99} for t in parsed.get("undergrad", []) if t in ug_titles],
            "grad_courses":      [{"title": t, "score": 99} for t in parsed.get("grad", [])     if t in grad_titles]
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

        prompt = f"""A University of Delaware student wants a semester-by-semester course roadmap.

Student Profile:
- Major: {major}
- Target Career: {career}
- Current Year: {year}
- Completed Courses: {courses if courses else 'None listed'}

Rules:
- Respect course prerequisites (e.g. intro courses before advanced ones)
- Each semester should build on the previous — sequence matters
- Do NOT include courses already completed by the student
- Start from where they are now ({year}) through graduation

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
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
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
